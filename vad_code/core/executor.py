"""Модуль исполнителя инструментов."""

import asyncio
import inspect
import time
from typing import Any, Callable, Optional

import json5

from vad_code.infrastructure.logger import log
from vad_code.infrastructure.backup_manager import backup_manager
from vad_code.infrastructure.audit_logger import audit_logger
from vad_code.infrastructure.metrics import session_metrics
from vad_code.infrastructure.error_messages import (
    format_error,
    get_available_tools_message,
)
from vad_code.tools.permissions import permission_manager, ToolRiskLevel


class ToolExecutionError(Exception):
    """Базовое исключение для ошибок выполнения инструментов."""

    pass


class ToolValidationError(ToolExecutionError):
    """Ошибка валидации аргументов."""

    pass


class ToolPermissionError(ToolExecutionError):
    """Ошибка доступа к инструменту."""

    pass


class ToolNotFoundError(ToolExecutionError):
    """Инструмент не найден."""

    pass


class ToolTimeoutError(ToolExecutionError):
    """Превышено время выполнения инструмента."""

    pass


class ToolExecutor:
    """Класс, отвечающий исключительно за выполнение зарегистрированных инструментов."""

    # Таймаут для выполнения инструментов (в секундах)
    DEFAULT_TIMEOUT = 120

    def __init__(self, timeout: Optional[int] = None) -> None:
        # Храним функции, их схемы и метаданные (включая уровень риска)
        self.tools: dict[str, Callable[..., Any]] = {}
        self.schemas: dict[str, Any] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        schema: Any = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Регистрация инструмента: имя, сама функция, Pydantic-схема и метаданные."""
        self.tools[name] = func
        if schema:
            self.schemas[name] = schema
        if metadata:
            self.metadata[name] = metadata

    def _parse_call_data(self, call_text: str) -> dict[str, Any]:
        """Парсит JSON-данные вызова инструмента."""
        try:
            call_data = json5.loads(call_text)
        except ValueError as e:
            raise ToolValidationError(f"Ошибка парсинга JSON: {e}") from e

        if not isinstance(call_data, dict):
            raise ToolValidationError("JSON должен быть объектом (словарем).")

        return call_data

    def _validate_tool_name(self, func_name: Optional[str]) -> str:
        """Валидирует имя инструмента."""
        if not func_name:
            raise ToolValidationError("В JSON не указано поле 'tool'.")
        if not isinstance(func_name, str):
            raise ToolValidationError("Поле 'tool' должно быть строкой.")
        if not func_name.strip():
            raise ToolValidationError("Поле 'tool' не может быть пустым.")
        return func_name.strip()

    def _check_permissions(self, func_name: str) -> None:
        """Проверяет разрешения для инструмента."""
        tool_meta = self.metadata.get(func_name, {})
        risk_level = tool_meta.get("risk_level", ToolRiskLevel.READ)

        if not permission_manager.is_allowed(risk_level):
            raise ToolPermissionError(
                f"Инструмент '{func_name}' (уровень риска: {risk_level.value}) "
                f"запрещен текущими настройками безопасности."
            )

    def _validate_arguments(
        self, func_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Валидирует аргументы через Pydantic-схему."""
        if func_name not in self.schemas:
            return args

        schema = self.schemas[func_name]
        try:
            validated_model = schema.model_validate(args)
            return validated_model.model_dump()  # type: ignore[no-any-return]
        except (ValueError, TypeError) as e:
            raise ToolValidationError(
                f"Ошибка валидации аргументов для '{func_name}': {e}"
            ) from e

    def _find_tool(self, func_name: str) -> Callable[..., Any]:
        """Находит зарегистрированный инструмент."""
        if func_name not in self.tools:
            available_tools = (
                ", ".join(sorted(self.tools.keys())) if self.tools else "нет"
            )
            raise ToolNotFoundError(
                f"Инструмент '{func_name}' не зарегистрирован. "
                f"Доступные инструменты: {available_tools}"
            )
        return self.tools[func_name]

    async def _execute_tool(
        self, func: Callable[..., Any], args: dict[str, Any]
    ) -> Any:
        """Выполняет инструмент с таймаутом."""
        try:
            if inspect.iscoroutinefunction(func):
                return await asyncio.wait_for(func(**args), timeout=self.timeout)
            else:
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(**args)),
                    timeout=self.timeout,
                )
        except asyncio.TimeoutError:
            raise ToolTimeoutError(
                f"Превышено время выполнения инструмента (таймаут: {self.timeout}с)"
            )

    def _get_affected_file_path(
        self, func_name: str, args: dict[str, Any]
    ) -> Optional[str]:
        """Пытается определить путь к файлу, который будет изменен."""
        # Приоритетные имена аргументов, содержащих путь
        path_keys = [
            "path",
            "file_path",
            "src",
            "source",
            "filename",
            "target",
            "dst",
            "destination",
        ]
        for key in path_keys:
            if key in args and isinstance(args[key], str):
                return str(args[key])
        # Если не нашли, возвращаем первый строковый аргумент
        for val in args.values():
            if isinstance(val, str):
                return str(val)
        return None

    async def execute(self, call_text: str) -> Optional[str]:
        """Выполняет зарегистрированный инструмент."""
        func_name: str = "unknown"
        args: dict[str, Any] = {}
        call_id: Optional[str] = None
        start_time = time.time()

        try:
            # 1. Парсинг JSON
            call_data = self._parse_call_data(call_text)
            raw_tool = call_data.get("tool")
            func_name = self._validate_tool_name(raw_tool)
            args = call_data.get("arguments", {})

            # 2. Валидация имени инструмента
            func_name = self._validate_tool_name(func_name)

            # 3. Проверка разрешений
            self._check_permissions(func_name)

            # 4. Лог начала вызова и аудит
            log.debug("🛠️ Tool Call: %s(%s)", func_name, args)
            call_id = audit_logger.start_call(func_name, args)

            # 5. Валидация аргументов
            final_args = self._validate_arguments(func_name, args)

            # 5.5. Создание бэкапа перед изменением (для WRITE и DANGEROUS)
            tool_meta = self.metadata.get(func_name, {})
            risk_level = tool_meta.get("risk_level", ToolRiskLevel.READ)

            if risk_level in (ToolRiskLevel.WRITE, ToolRiskLevel.DANGEROUS):
                affected_path = self._get_affected_file_path(func_name, final_args)
                if affected_path:
                    backup_manager.create_backup(affected_path, operation=func_name)

            # 6. Поиск инструмента
            func = self._find_tool(func_name)

            # 7. Выполнение
            result = await self._execute_tool(func, final_args)

            # 8. Измерение времени и запись метрик
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=True)

            # 9. Лог успеха и аудит
            log.debug("✅ Success: %s completed in %.2fs.", func_name, execution_time)
            result_str = str(result) if result is not None else "Success"

            if call_id:
                audit_logger.end_call(call_id, result_str, success=True)

            return result_str

        except ToolValidationError as e:
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.error("❌ Validation Error: %s", e)
            error_msg = format_error("validation_error", tool_name=func_name)
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
        except ToolPermissionError as e:
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.warning("🚫 Permission Denied: %s", e)
            allowed = (
                [level.value for level in permission_manager.allowed_levels]
                if permission_manager.allowed_levels
                else []
            )

            # Получаем risk_level заново, так как проверка могла произойти до его определения
            tool_meta = self.metadata.get(func_name, {})
            risk_level = tool_meta.get("risk_level", ToolRiskLevel.READ)

            error_msg = format_error(
                "permission_denied",
                tool_name=func_name,
                risk_level=risk_level.value,
                allowed_levels=allowed,
            )
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
        except ToolNotFoundError as e:
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.error("❌ Tool Not Found: %s", e)
            available = sorted(self.tools.keys()) if self.tools else []
            error_msg = format_error(
                "tool_not_found",
                tool_name=func_name,
                available_tools=get_available_tools_message(available),
            )
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
        except ToolTimeoutError as e:
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.error("⏱️ Timeout: %s", e)
            error_msg = format_error(
                "timeout_error", tool_name=func_name, timeout=self.timeout
            )
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
        except ToolExecutionError as e:
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.error("💥 Tool Execution Error: %s", e)
            error_msg = format_error(
                "unexpected_error",
                error_type_name=type(e).__name__,
                error_message=str(e),
                message=f"Ошибка выполнения '{func_name}'",
                suggestion="Проверьте параметры инструмента и попробуйте снова.",
            )
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
        except Exception as e:
            # Неожиданные ошибки
            execution_time = time.time() - start_time
            session_metrics.record_tool_call(func_name, execution_time, success=False)
            log.exception("💥 Unexpected Error: %s", e)
            error_msg = format_error(
                "unexpected_error",
                error_type_name=type(e).__name__,
                error_message=str(e),
                message=f"Неожиданная ошибка в '{func_name}'",
                suggestion="Проверьте логи для деталей.",
            )
            if call_id:
                audit_logger.end_call(
                    call_id, error_msg, success=False, error_message=str(e)
                )
            return error_msg
