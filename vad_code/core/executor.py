import json
import traceback
from typing import Optional, Callable, Any


class ToolExecutor:
    """Класс, отвечающий исключительно за выполнение зарегистрированных инструментов."""

    def __init__(self) -> None:
        # Храним функции и их схемы отдельно
        self.tools: dict[str, Callable] = {}
        self.schemas: dict[str, Any] = {}

    def register_tool(self, name: str, func: Callable, schema: Any = None) -> None:
        """Регистрация инструмента: имя, сама функция и Pydantic-схема."""
        self.tools[name] = func
        if schema:
            self.schemas[name] = schema

    async def execute(self, call_text: str) -> Optional[str]:
        """Парсит JSON, валидирует через зарегистрированные схемы и вызывает функцию."""
        func_name = None
        try:
            call_data = json.loads(call_text)
            func_name = call_data.get("tool")
            args = call_data.get("arguments", {})

            if not func_name:
                return "Ошибка: В JSON не указано поле 'tool'."

            # 1. Валидация, если для этого инструмента есть схема
            final_args = args
            if func_name in self.schemas:
                schema = self.schemas[func_name]
                try:
                    validated_model = schema.model_validate(args)
                    final_args = validated_model.model_dump()
                except Exception as e:
                    return f"Ошибка валидации аргументов: {e}"

            # 2. Проверка наличия функции
            if func_name not in self.tools:
                return f"Ошибка: Инструмент '{func_name}' не зарегистрирован."

            # 3. Вызов
            func = self.tools[func_name]
            import inspect
            if inspect.iscoroutinefunction(func):
                result = await func(**final_args)
            else:
                result = func(**final_args)

            return str(result) if result is not None else "Success"

        except json.JSONDecodeError:
            return "Ошибка: Некорректный формат JSON."
        except Exception as e:
            return f"Ошибка при выполнении инструмента '{func_name}':\n{traceback.format_exc()}"
