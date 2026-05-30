"""Модуль агента — управляет историей, системным промптом и циклом вызовов инструментов"""

import re
from typing import Any

import json5

from vad_code.config import settings
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_providers import BaseLLMProvider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.infrastructure.bad_cases import bad_case_manager
from vad_code.infrastructure.backup_manager import backup_manager
from vad_code.infrastructure.audit_logger import audit_logger
from vad_code.core.memory import ConversationMemory

MAX_OBSERVATION_CHARS = 30_000


class Agent:
    """Агент: управляет историей, формирует промпт и запускает цикл выполнения задач."""

    def __init__(
        self,
        llm_client: BaseLLMProvider,
        executor: ToolExecutor,
        tokenizer: Tokenizer,
    ) -> None:
        """
        Инициализация агента через внедрение зависимостей.

        :param llm_client: Провайдер для взаимодействия с LLM.
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

        # Статистика сессии
        self.session_stats = {
            "tool_calls": 0,
            "total_tokens": 0,
            "errors": 0,
            "iterations": 0,
        }

    # ------------------------------------------------------------------
    # Системный промпт
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Строит системный промпт на основе зарегистрированных инструментов."""
        # Берем инструменты из executor, а не из TOOL_REGISTRY
        # чтобы включить мульти-агентные инструменты
        tools_text = "\n".join(
            f"{i + 1}. {name}(...) - "
            f"{self.executor.metadata.get(name, {}).get('description', 'Нет описания')}"
            for i, name in enumerate(self.executor.tools.keys())
        )

        # Определяем доступные уровни риска
        from vad_code.tools.permissions import permission_manager

        if permission_manager.allowed_levels is None:
            risk_info = "Все уровни разрешены (read, write, dangerous)"
        else:
            risk_info = ", ".join(
                level.value for level in permission_manager.allowed_levels
            )

        # Проверяем, есть ли мульти-агентные инструменты
        has_multi_agent = "execute_with_agent" in self.executor.tools

        multi_agent_section = ""
        if has_multi_agent:
            multi_agent_section = (
                "\nМУЛЬТИ-АГЕНТНАЯ СИСТЕМА:\n"
                "У вас есть доступ к специализированным агентам для сложных задач:\n"
                "- code_review: проверка кода на ошибки и лучшие практики\n"
                "- testing: написание и запуск тестов\n"
                "- documentation: генерация документации\n"
                "- security: аудит безопасности кода\n\n"
                "Используйте execute_with_agent для делегирования задач "
                "специализированным агентам.\n"
                "Используйте execute_parallel_tasks для параллельного "
                "выполнения нескольких задач.\n"
                "Используйте route_task для проверки, какой агент "
                "лучше подходит для задачи.\n\n"
            )

        return (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{settings.project_root}. "
            "Твоя задача - помогать пользователю анализировать и изменять код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            f"{tools_text}\n\n"
            f"{multi_agent_section}"
            "УРОВНИ РИСКА ИНСТРУМЕНТОВ:\n"
            "- READ: чтение файлов, просмотр структуры, git-лог (безопасно)\n"
            "- WRITE: запись файлов, создание директорий, git-коммиты "
            "(изменяет файлы)\n"
            "- DANGEROUS: удаление файлов, выполнение команд "
            "(требует осторожности)\n"
            f"Текущие разрешения: {risk_info}\n\n"
            "ПРОТОКОЛ ВЗАИМОДЕЙСТВИЯ:\n"
            "1. Вызов инструмента — СТРОГО отдельный блок JSON, "
            "без другого текста на этих строках:\n"
            "```json\n"
            "{\n"
            '  "tool": "имя_функции",\n'
            '  "arguments": {"аргумент1": "значение1"}\n'
            "}\n"
            "```\n\n"
            "2. Не используй ```json в примерах или объяснениях — "
            "только для реального вызова.\n\n"
            "3. После каждого вызова ты получишь: OBSERVATION: [результат]\n\n"
            "4. Когда информации достаточно — напиши финальный ответ "
            "без блока ```json.\n\n"
            "5. Никогда не выдумывай содержимое файлов, "
            "используй только read_file.\n\n"
            "ПРАВИЛА РАБОТЫ:\n"
            "- Перед изменением файла всегда читай его содержимое "
            "через read_file\n"
            "- Для больших файлов используй read_file_lines "
            "вместо read_file\n"
            "- Перед удалением файла подтверди путь через list_files "
            "или list_tree\n"
            "- Используй search_in_files вместо последовательных "
            "read_file для поиска\n"
            "- Для изучения структуры проекта используй list_tree\n"
            "- Git-операции выполняй последовательно: "
            "status -> diff -> add -> commit\n"
            "- Если получил ошибку доступа, не пытайся выполнить "
            "запрещенный инструмент\n"
            "- Всегда проверяй результат выполнения инструмента "
            "перед следующим шагом"
        )

    # ------------------------------------------------------------------
    # История
    # ------------------------------------------------------------------

    def reset_history(self) -> None:
        """Очищает историю сообщений через объект памяти."""
        self.memory.reset()

    def undo(self) -> str:
        """Отменяет последнее изменение файла."""
        return backup_manager.undo() or "Нет изменений для отмены."

    def redo(self) -> str:
        """Повторяет отмененное изменение."""
        return backup_manager.redo() or "Нет изменений для повтора."

    def get_change_history(self) -> list[dict[str, Any]]:
        """Возвращает историю изменений файлов."""
        return backup_manager.get_history()

    def get_audit_records(self, limit: int = 50) -> str:
        """Возвращает журнал аудита действий."""
        records = audit_logger.get_records(limit=limit)
        return audit_logger.format_records(records)

    def get_audit_stats(self) -> str:
        """Возвращает статистику по вызовам инструментов."""
        stats = audit_logger.get_stats()
        lines = [
            "📊 Статистика вызовов инструментов:",
            f"  Всего вызовов: {stats['total_calls']}",
            f"  Успешных: {stats['successful_calls']}",
            f"  Ошибок: {stats['failed_calls']}",
            f"  Среднее время: {stats['avg_duration_ms']}ms",
        ]
        if stats["tools_used"]:
            lines.append("\n  По инструментам:")
            for tool, tool_stats in stats["tools_used"].items():
                lines.append(
                    f"    - {tool}: {tool_stats['count']} вызовов, "
                    f"{tool_stats['avg_duration_ms']}ms среднее"
                )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_call(ai_response: str) -> str | None:
        """Извлекает ПОСЛЕДНИЙ валидный JSON-вызов инструмента из ответа AI."""
        candidates = []
        # 1. Ищем в блоках ```json ... ```
        json_blocks = re.finditer(r"```json\s*(.*?)\s*```", ai_response, re.DOTALL)
        for match in json_blocks:
            content = match.group(1)
            parsed = Agent._try_parse_json(content)
            if parsed:
                candidates.append(content)
        # 2. Ищем в любых блоках ``` ... ```
        if not candidates:
            code_blocks = re.finditer(r"```\s*(.*?)\s*```", ai_response, re.DOTALL)
            for match in code_blocks:
                content = match.group(1)
                parsed = Agent._try_parse_json(content)
                if parsed:
                    candidates.append(content)
        # 3. Пытаемся найти JSON-объект в тексте
        if not candidates:
            start = ai_response.find("{")
            end = ai_response.rfind("}")
            if start != -1 and end != -1 and start < end:
                candidate = ai_response[start : end + 1]
                if Agent._try_parse_json(candidate):
                    candidates.append(candidate)
        return candidates[-1] if candidates else None

    @staticmethod
    def _balance_braces(text: str) -> str:
        """Балансирует фигурные и квадратные скобки в тексте."""
        # Считаем баланс скобок, игнорируя те, что внутри строк
        in_string = False
        escape_next = False
        brace_count = 0  # для {}
        bracket_count = 0  # для []
        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
        # Добавляем недостающие закрывающие скобки
        result = text
        if brace_count > 0:
            result += "}" * brace_count
        if bracket_count > 0:
            result += "]" * bracket_count
        return result

    @staticmethod
    def _try_parse_json(text: str) -> bool:
        """Пытается распарсить текст как JSON и проверить наличие ключа 'tool'."""
        # Сначала пробуем распарсить как есть
        try:
            data = json5.loads(text)
            return isinstance(data, dict) and "tool" in data
        except ValueError:
            pass

        # Пытаемся исправить распространенные ошибки JSON от LLM
        strategies = [
            # Стратегия 1: базовое исправление (переносы строк + баланс скобок)
            lambda t: Agent._balance_braces(re.sub(r"(?<!\\)\n", "\\n", t)),
            # Стратегия 2: удаление лишних закрывающих скобок в конце
            lambda t: Agent._remove_trailing_braces(t),
            # Стратегия 3: комбинация
            lambda t: Agent._remove_trailing_braces(re.sub(r"(?<!\\)\n", "\\n", t)),
            # Стратегия 4: попытка найти валидный JSON-подстроку
            lambda t: Agent._extract_json_substring(t),
        ]

        for strategy in strategies:
            try:
                fixed_text = strategy(text)  # type: ignore[no-untyped-call]
                if fixed_text and fixed_text != text:
                    data = json5.loads(fixed_text)
                    if isinstance(data, dict) and "tool" in data:
                        return True
            except ValueError:
                continue

        return False

    @staticmethod
    def _remove_trailing_braces(text: str) -> str:
        """Удаляет лишние закрывающие скобки в конце JSON."""
        stripped = text.rstrip()
        while stripped and stripped[-1] in ("}", "]"):
            candidate = stripped[:-1]
            try:
                json5.loads(candidate)
                stripped = candidate
            except ValueError:
                break
        return stripped

    @staticmethod
    def _extract_json_substring(text: str) -> str | None:
        """Пытается найти валидный JSON-объект внутри текста."""
        start = text.find("{")
        if start == -1:
            return None

        for end in range(len(text) - 1, start, -1):
            if text[end] == "}":
                candidate = text[start : end + 1]
                try:
                    json5.loads(candidate)
                    return candidate
                except ValueError:
                    continue
        return None

    @staticmethod
    def _get_tool_name(call_json: str) -> str:
        try:
            return str(json5.loads(call_json).get("tool", "?"))
        except ValueError:
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

    def print_stats(self) -> None:
        """Выводит статистику текущей сессии."""
        stats = self.session_stats
        log.info(
            "\n📊 Статистика сессии:\n"
            "  Вызовов инструментов: %d\n"
            "  Всего токенов: %d\n"
            "  Ошибок: %d\n"
            "  Итераций: %d\n"
            "  Сообщений в памяти: %d\n",
            stats["tool_calls"],
            stats["total_tokens"],
            stats["errors"],
            stats["iterations"],
            len(self.memory.history),
        )

    async def handle(self, user_input: str) -> None:
        """Обрабатывает один запрос пользователя"""
        self.memory.add_message("user", user_input)

        for i in range(settings.max_iterations):
            self.session_stats["iterations"] += 1
            self.memory.trim()
            ai_response = await self.llm_client.complete_with_retry(
                self.memory.get_messages(),
                max_retries=3,
                base_delay=1.0,
            )
            self.memory.add_message("assistant", ai_response)

            # Подсчет токенов
            current_tokens = self.tokenizer.count_tokens(ai_response)
            self.session_stats["total_tokens"] += current_tokens

            call_json = self._extract_call(ai_response)

            if call_json:
                self.session_stats["tool_calls"] += 1
                observation = await self.executor.execute(call_json)

                if observation is None:
                    # Невалидный вызов — считаем финальным ответом
                    self.session_stats["errors"] += 1
                    # Сохраняем проблемный случай
                    bad_case_manager.add_case(
                        user_input=user_input,
                        ai_response=ai_response,
                        error_type="invalid_call",
                        error_details="Вызов инструмента распознан, но не выполнен",
                        context={"iteration": i + 1},
                    )
                    log.info("\n🤖 AI: %s\n", ai_response)
                    return

                tool_name = self._get_tool_name(call_json)
                log.info(
                    "🤖 AI вызывает [%s]... (%d/%d)",
                    tool_name,
                    i + 1,
                    settings.max_iterations,
                )
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
                # AI не сгенерировал вызов инструмента - это потенциально проблемный случай
                # если пользователь ожидал действия
                log.info("\n🤖 AI: %s\n", ai_response)
                return

        log.error("\n⚠️ Достигнут лимит итераций.")

    async def close(self) -> None:
        """Закрывает сетевые соединения агента"""
        await self.llm_client.close()
