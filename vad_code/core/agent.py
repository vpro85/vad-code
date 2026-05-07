"""Модуль агента — управляет историей, системным промптом и циклом вызовов инструментов"""
import json
import re

from vad_code.config import settings
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.infrastructure.logger import log
from vad_code.tools.file_tools import TOOL_REGISTRY

# Сколько символов одного OBSERVATION сохраняем в историю.
# Намеренно меньше max_chars в _trim_history (40_000),
# чтобы одна observation не занимала весь контекстный бюджет.
MAX_OBSERVATION_CHARS = 2_000

# Лимит суммарного объёма истории в символах
MAX_HISTORY_CHARS = 40_000


class Agent:
    """Агент: управляет историей, формирует промпт и запускает цикл выполнения задач."""

    def __init__(self, llm_client: LLMClient, executor: ToolExecutor) -> None:
        self.llm_client = llm_client
        self.executor = executor
        self.history: list[dict] = []
        self.system_prompt = self._build_system_prompt()

    # ------------------------------------------------------------------
    # Системный промпт
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        tools_text = "\n".join(
            f"{i + 1}. {name}(...) - {info['description']}"
            for i, (name, info) in enumerate(TOOL_REGISTRY.items())
        )
        return (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{settings.project_root}. "
            "Твоя задача - помогать пользователю анализировать и изменять код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            f"{tools_text}\n\n"
            "ПРОТОКОЛ ВЗАИМОДЕЙСТВИЯ:\n"
            "- Вызов инструмента — СТРОГО отдельный блок JSON, без другого текста на этих строках:\n"
            "```json\n"
            "{\n"
            '  "tool": "имя_функции",\n'
            '  "arguments": {"аргумент1": "значение1"}\n'
            "}\n"
            "```\n"
            "- Не используй ```json в примерах или объяснениях — только для реального вызова.\n"
            "- После каждого вызова ты получишь: OBSERVATION: [результат]\n"
            "- Когда информации достаточно — напиши финальный ответ без блока ```json.\n"
            "- Никогда не выдумывай содержимое файлов, используй только read_file."
        )

    # ------------------------------------------------------------------
    # История
    # ------------------------------------------------------------------

    def _trim_history(self) -> None:
        """Обрезает историю, сохраняя первое сообщение сессии."""
        # 1. Лимит по количеству сообщений
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent

        # 2. Лимит по объёму символов — удаляем только валидные пары
        total_chars = sum(len(m["content"]) for m in self.history)

        idx = 1  # первое сообщение (запрос сессии) не трогаем
        while total_chars > MAX_HISTORY_CHARS and idx + 1 < len(self.history):
            msg_a = self.history[idx]
            msg_b = self.history[idx + 1]
            # Удаляем только пару: assistant → user(OBSERVATION)
            if (
                msg_a["role"] == "assistant"
                and msg_b["role"] == "user"
                and msg_b["content"].startswith("OBSERVATION:")
            ):
                total_chars -= len(msg_a["content"]) + len(msg_b["content"])
                del self.history[idx: idx + 2]
            else:
                idx += 1

    def _build_messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.history

    # ------------------------------------------------------------------
    # Парсинг вызова инструмента
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_call(ai_response: str) -> str | None:
        """
        Извлекает валидный JSON-объект из ответа модели.

        Стратегия многоуровневая — от строгой к мягкой:
        1. Ищем ```json ... ``` блок (канонический формат).
        2. Ищем любой {...} объект, содержащий ключ "tool" — страховка
           на случай если модель забыла обернуть блок в тройные кавычки.
        3. Если найденная строка не парсится как JSON — возвращаем None,
           чтобы агент не передавал мусор в executor.
        """
        # 1. Канонический формат: ```json ... ```
        # re.DOTALL нужен чтобы захватить многострочный JSON внутри блока
        match = re.search(r"```json\s*(\{.*?\})\s*```", ai_response, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if _is_valid_tool_call(candidate):
                return candidate

        # 2. Мягкий fallback: любой {...} с ключом "tool"
        # Жадный поиск от первой { до последней } — это важно для
        # многострочных JSON с вложенными объектами в аргументах.
        match = re.search(r"(\{[^`]*?\"tool\"\s*:[^`]*?\})", ai_response, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if _is_valid_tool_call(candidate):
                log.debug("Использован fallback-парсинг tool call (без ```json```)")
                return candidate

        return None

    @staticmethod
    def _get_tool_name(call_json: str) -> str:
        try:
            return json.loads(call_json).get("tool", "?")
        except Exception:
            return "?"

    @staticmethod
    def _truncate_observation(observation: str) -> str:
        """Обрезает OBSERVATION перед сохранением в историю."""
        if len(observation) <= MAX_OBSERVATION_CHARS:
            return observation
        return (
            observation[:MAX_OBSERVATION_CHARS]
            + f"\n[... обрезано, всего {len(observation)} символов ...]"
        )

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------

    async def handle(self, user_input: str) -> None:
        """Обрабатывает один запрос пользователя."""
        self.history.append({"role": "user", "content": user_input})

        for i in range(settings.max_iterations):
            self._trim_history()
            ai_response = await self.llm_client.complete(self._build_messages())
            self.history.append({"role": "assistant", "content": ai_response})

            call_json = self._extract_call(ai_response)

            if call_json:
                # executor.execute() синхронный — не await
                observation = self.executor.execute(call_json)

                if observation is None:
                    # Невалидный вызов — считаем финальным ответом
                    log.info("agent.final_answer", response_preview=ai_response[:200])
                    print(f"\n🤖 AI: {ai_response}\n")
                    return

                tool_name = self._get_tool_name(call_json)
                log.info(
                    "agent.tool_call",
                    tool=tool_name,
                    iteration=f"{i + 1}/{settings.max_iterations}",
                    result_preview=observation[:120],
                )
                print(f"🤖 [{tool_name}] ({i + 1}/{settings.max_iterations})")
                print(f"   {observation[:120]}{'...' if len(observation) > 120 else ''}")

                self.history.append({
                    "role": "user",
                    "content": f"OBSERVATION: {self._truncate_observation(observation)}",
                })
            else:
                log.info("agent.final_answer", response_preview=ai_response[:200])
                print(f"\n🤖 AI: {ai_response}\n")
                return

        log.error("agent.iteration_limit_reached", max_iterations=settings.max_iterations)
        print("\n⚠️ Достигнут лимит итераций.")

    async def close(self) -> None:
        """Закрывает сетевые соединения агента."""
        await self.llm_client.close()


# ------------------------------------------------------------------
# Вспомогательная функция (модульный уровень — не метод класса,
# чтобы _extract_call оставался @staticmethod без self)
# ------------------------------------------------------------------

def _is_valid_tool_call(text: str) -> bool:
    """Возвращает True если строка — валидный JSON с ключом 'tool'."""
    try:
        data = json.loads(text)
        return isinstance(data, dict) and "tool" in data
    except json.JSONDecodeError:
        return False