"""Модуль агента — управляет историей, системным промптом и циклом вызовов инструментов"""
import json
import re

from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.tools.file_tools import TOOL_REGISTRY
from vad_code.config import settings


class Agent:
    """Агент: хранит историю, формирует промпт, управляет циклом tool-call"""

    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self.executor = ToolExecutor()
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
        """Обрезает историю, сохраняя первое сообщение сессии"""
        # 1. Лимит по количеству сообщений
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent

        # 2. Лимит по объему символов — удаляем пары (assistant + observation)
        max_chars = 40_000
        total_chars = sum(len(m["content"]) for m in self.history)

        idx = 1  # никогда не трогаем первое сообщение (индекс 0)
        while total_chars > max_chars and idx + 1 < len(self.history):
            msg_a = self.history[idx]
            msg_b = self.history[idx + 1]
            # Удаляем только валидную пару: assistant → user(OBSERVATION)
            if (
                msg_a["role"] == "assistant"
                and msg_b["role"] == "user"
                and msg_b["content"].startswith("OBSERVATION:")
            ):
                total_chars -= len(msg_a["content"]) + len(msg_b["content"])
                del self.history[idx: idx + 2]
            else:
                idx += 1  # пропускаем «не пару»

    def _build_messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.history

    # ------------------------------------------------------------------
    # Парсинг вызова инструмента
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_call(ai_response: str) -> str | None:
        """Извлекает JSON из блока ```json...``` если он есть"""
        match = re.search(r"```json\s*(.*?)\s*```", ai_response, re.DOTALL)
        return match.group(1) if match else None

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------

    def handle(self, user_input: str) -> None:
        """Обрабатывает один запрос пользователя"""
        self.history.append({"role": "user", "content": user_input})

        for i in range(settings.max_iterations):
            self._trim_history()
            ai_response = self.llm_client.complete(self._build_messages())
            self.history.append({"role": "assistant", "content": ai_response})

            call_json = self._extract_call(ai_response)

            if call_json:
                observation = self.executor.execute(call_json)

                if observation is None:
                    # Невалидный вызов — считаем финальным ответом
                    print(f"\n🤖 AI: {ai_response}\n")
                    return

                tool_name = self._get_tool_name(call_json)
                print(f"🤖 AI вызывает [{tool_name}]... ({i + 1}/{settings.max_iterations})")
                print(f"📝 Результат: {observation[:120]}{'...' if len(observation) > 120 else ''}")
                self.history.append({"role": "user", "content": f"OBSERVATION: {observation}"})
            else:
                print(f"\n🤖 AI: {ai_response}\n")
                return

        print("\n⚠️ Достигнут лимит итераций.")

    @staticmethod
    def _get_tool_name(call_json: str) -> str:
        try:
            return json.loads(call_json).get("tool", "?")
        except Exception:
            return "?"
