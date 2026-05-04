import inspect
import json
import traceback
from typing import Optional

from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY


class ToolExecutor:
    """Класс, отвечающий за выполнение инструментов (tool calls)"""

    def __init__(self) -> None:
        self.file_tools = FileTools()
        self.tools = {}
        # Привязываем методы к словарю для быстрого доступа
        for name in TOOL_REGISTRY:
            if hasattr(self.file_tools, name):
                method = getattr(self.file_tools, name)
                self.tools[name] = method

    async def execute(self, call_text: str) -> Optional[str]:
        """
        Парсит JSON-строку, валидирует аргументы через Pydantic и вызывает функцию.
        Возвращает результат выполнения или сообщение об ошибке.
        """
        func_name = None
        try:
            # 1. Парсим JSON
            call_data = json.loads(call_text)
            func_name = call_data.get("tool")
            args = call_data.get("arguments", {})

            if not func_name:
                return "Ошибка: В JSON не указано поле 'tool'."

            # 2. Валидация аргументов через Pydantic
            final_args = args
            if func_name in TOOL_REGISTRY:
                schema = TOOL_REGISTRY[func_name].get("schema")
                if schema:
                    try:
                        # Сохраняем результат валидации (здесь происходит приведение типов)
                        validated_model = schema.model_validate(args)
                        final_args = validated_model.model_dump()
                    except Exception as e:
                        return f"Ошибка валидации аргументов: {e}"

            # 3. Вызов функции
            if func_name not in self.tools:
                return f"Ошибка: Функция '{func_name}' не поддерживается."

            func = self.tools[func_name]
            if inspect.iscoroutinefunction(func):
                result = await func(**final_args)
            else:
                result = func(**final_args)

            return str(result) if result is not None else "Success"

        except Exception as e:
            # Формируем подробный отчет об ошибке для агента
            error_details = traceback.format_exc()
            return f"❌ Ошибка при выполнении инструмента '{func_name}':\n{error_details}"
