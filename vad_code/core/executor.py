"""Модуль исполнителя инструментов."""
import inspect
import json
from typing import Any, Callable, Optional


class ToolExecutor:
    """Класс, отвечающий исключительно за выполнение зарегистрированных инструментов."""

    def __init__(self) -> None:
        # Храним функции и их схемы отдельно
        self.tools: dict[str, Callable[..., Any]] = {}
        self.schemas: dict[str, Any] = {}

    def register_tool(self, name: str, func: Callable[..., Any], schema: Any = None) -> None:
        """Регистрация инструмента: имя, сама функция и Pydantic-схема."""
        self.tools[name] = func
        if schema:
            self.schemas[name] = schema

    async def execute(self, call_text: str) -> Optional[str]:
        """Выполняет зарегистрированный инструмент."""
        try:
            call_data = json.loads(call_text)
            func_name = call_data.get("tool")
            args = call_data.get("arguments", {})

            if not func_name:
                return "Ошибка: В JSON не указано поле 'tool'."

            # --- ДОБАВЛЕНО: Лог начала вызова ---
            print(f"\n[🛠️ Tool Call] {func_name}({args})")
            # ------------------------------------

            final_args = args
            if func_name in self.schemas:
                schema = self.schemas[func_name]
                try:
                    validated_model = schema.model_validate(args)
                    final_args = validated_model.model_dump()
                except (ValueError, TypeError) as e:
                    error_msg = f"Ошибка валидации аргументов: {e}"
                    print(f"[❌ Validation Error] {error_msg}")  # --- ДОБАВЛЕНО ---
                    return error_msg

            if func_name not in self.tools:
                error_msg = f"Ошибка: Инструмент '{func_name}' не зарегистрирован."
                print(f"[❌ Tool Not Found] {error_msg}")  # --- ДОБАВЛЕНО ---
                return error_msg

            func = self.tools[func_name]
            if inspect.iscoroutinefunction(func):
                result = await func(**final_args)
            else:
                result = func(**final_args)

            # --- ДОБАВЛЕНО: Лог успеха ---
            print(f"[✅ Success] {func_name} completed.")
            # -----------------------------

            return str(result) if result is not None else "Success"
        except (ValueError, TypeError, OSError) as e:
            error_msg = f"Ошибка при выполнении инструмента: {str(e)}"
            print(f"[💥 Critical Error] {error_msg}")  # --- ДОБАВЛЕНО ---
            return error_msg
