"""Модуль агента — управляет историей, системным промптом и циклом вызовов инструментов"""
import json
import re

from vad_code.config import settings
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.core.memory import ConversationMemory
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

        # Теперь агент не знает о FileTools, он просто использует то, что есть в executor.
        # Системный промпт строится на основе того, что зарегистрировано в TOOL_REGISTRY.
        self.system_prompt = self._build_system_prompt()
        self.memory = ConversationMemory(tokenizer, self.system_prompt)

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
            "- Вызов инструмента — СТРОГО отдельный блок JSON, "
            "без другого текста на этих строках:\n"
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

    def reset_history(self) -> None:
        """Очищает историю сообщений через объект памяти."""
        self.memory.reset()

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
                    return str(candidate)
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    @staticmethod
    def _get_tool_name(call_json: str) -> str:
        try:
            return str(json.loads(call_json).get("tool", "?"))
        except (json.JSONDecodeError, ValueError):
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
        self.memory.add_message("user", user_input)

        for i in range(settings.max_iterations):
            self.memory.trim()
            ai_response = await self.llm_client.complete(self.memory.get_messages())
            self.memory.add_message("assistant", ai_response)

            call_json = self._extract_call(ai_response)

            if call_json:
                observation = await self.executor.execute(call_json)

                if observation is None:
                    # Невалидный вызов — считаем финальным ответом
                    log.info("\n🤖 AI: %s\n", ai_response)
                    return

                tool_name = self._get_tool_name(call_json)
                log.info("🤖 AI вызывает [%s]... (%d/%d)", tool_name, i + 1, settings.max_iterations)
                log.info(
                    "📝 Результат: %s%s",
                    observation[:120],
                    "..." if len(observation) > 120 else "",
                )

                # Сохраняем усечённую версию — полный контент не нужен в истории
                self.memory.add_message(
                    "user", f"OBSERVATION: {self._truncate_observation(observation)}"
                )
            else:
                log.info("\n🤖 AI: %s\n", ai_response)
                return

        log.error("\n⚠️ Достигнут лимит итераций.")

    async def close(self) -> None:
        """Закрывает сетевые соединения агента"""
        await self.llm_client.close()
