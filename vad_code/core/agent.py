"""Модуль агента — управляет историей, системным промптом и циклом вызовов инструментов"""
import json
import re

from vad_code.config import settings
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.tools.file_tools import TOOL_REGISTRY

MAX_OBSERVATION_CHARS = 30_000


class Agent:
    """Агент: управляет историей, формирует промпт и запускает цикл выполнения задач."""

    def __init__(self, llm_client: LLMClient, executor: ToolExecutor, tokenizer: Tokenizer) -> None:
        """
        Инициализация агента через внедрение зависимостей.

        :param llm_client: Клиент для взаимодействия с LLM.
        :param executor: Объект, содержащий зарегистрированные инструменты.
        :param tokenizer: Токенизатор для подсчета длины контекста.
        """
        self.llm_client = llm_client
        self.executor = executor
        self.tokenizer = tokenizer
        self.history: list[dict] = []

        # Теперь агент не знает о FileTools, он просто использует то, что есть в executor.
        # Системный промпт строится на основе того, что зарегистрировано в TOOL_REGISTRY.
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
        """Обрезает историю, сохраняя первое сообщение сессии и соблюдая лимиты токенов."""
        # 1. Лимит по количеству сообщений (сохраняем системное/первое сообщение)
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent

        # 2. Лимит по количеству токенов
        system_tokens = self.tokenizer.count_tokens(self.system_prompt)
        total_tokens = system_tokens + self.tokenizer.count_messages_tokens(self.history)
        log.debug(f"Current history size: {total_tokens} tokens, {len(self.history)} messages")

        if total_tokens <= settings.max_context_tokens:
            return

        idx = 1  # Никогда не трогаем первое сообщение (индекс 0)
        while total_tokens > settings.max_context_tokens and idx + 1 < len(self.history):
            msg_a = self.history[idx]
            msg_b = self.history[idx + 1]
            
            # Пытаемся удалять пары: [assistant (tool call)] + [user (observation)]
            if (
                msg_a["role"] == "assistant"
                and msg_b["role"] == "user"
                and msg_b["content"].startswith("OBSERVATION:")
            ):
                # Считаем токены удаляемой пары (роль + контент для каждого сообщения)
                pair_tokens = (self.tokenizer.count_tokens(msg_a["role"]) +
                               self.tokenizer.count_tokens(msg_a["content"]) +
                               self.tokenizer.count_tokens(msg_b["role"]) +
                               self.tokenizer.count_tokens(msg_b["content"]))
                total_tokens -= pair_tokens
                del self.history[idx : idx + 2]
            else:
                # Если пара не подходит под паттерн, просто сдвигаемся дальше
                idx += 1

    def _build_messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.history

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_call(ai_response: str) -> str | None:
        """Извлекает ПОСЛЕДНИЙ JSON из блоков ```json...```, если он содержит ключ 'tool'"""
        matches = re.findall(r"```json\s*(.*?)\s*```", ai_response, re.DOTALL)
        if not matches:
            return None

        # Проверяем блоки с конца, чтобы найти первый валидный вызов инструмента
        for candidate in reversed(matches):
            try:
                data = json.loads(candidate)
                if isinstance(data, dict) and "tool" in data:
                    return candidate
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    @staticmethod
    def _get_tool_name(call_json: str) -> str:
        try:
            return json.loads(call_json).get("tool", "?")
        except Exception:
            return "?"

    @staticmethod
    def _truncate_observation(observation: str) -> str:
        """Обрезает большие OBSERVATION, чтобы не раздувать контекст"""
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
        """Обрабатывает один запрос пользователя"""
        self.history.append({"role": "user", "content": user_input})

        for i in range(settings.max_iterations):
            self._trim_history()
            ai_response = await self.llm_client.complete(self._build_messages())
            self.history.append({"role": "assistant", "content": ai_response})

            call_json = self._extract_call(ai_response)

            if call_json:
                observation = await self.executor.execute(call_json)

                if observation is None:
                    # Невалидный вызов — считаем финальным ответом
                    log.info(f"\n🤖 AI: {ai_response}\n")
                    return

                tool_name = self._get_tool_name(call_json)
                log.info(f"🤖 AI вызывает [{tool_name}]... ({i + 1}/{settings.max_iterations})")
                log.info(f"📝 Результат: {observation[:120]}{'...' if len(observation) > 120 else ''}")

                # Сохраняем усечённую версию — полный контент не нужен в истории
                self.history.append({
                    "role": "user",
                    "content": f"OBSERVATION: {self._truncate_observation(observation)}",
                })
            else:
                log.info(f"\n🤖 AI: {ai_response}\n")
                return

        log.error("\n⚠️ Достигнут лимит итераций.")

    async def close(self) -> None:
        """Закрывает сетевые соединения агента"""
        await self.llm_client.close()
