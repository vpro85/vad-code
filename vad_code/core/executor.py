import json
from typing import Optional, Any

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

    def execute(self, call_text: str) -> Optional[str]:
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

            # 2. Валидация аргументов через Pydantic (если схема есть в реестре)
            if func_name in TOOL_REGISTRY:
                schema = TOOL_REGISTRY[func_name].get("schema")
                if schema:
                    try:
                        schema.model_validate(args)
                    except Exception as e:
                        return f"Ошибка валидации аргументов: {e}"

            # 3. Вызов функции
            if func_name not in self.tools:
                return f"Ошибка: Функция '{func_name}' не поддерживается."

            return self.tools[func_name](**args)

        except json.JSONDecodeError as e:
            return f"Ошибка: Некорректный формат JSON. {e}"
        except TypeError as e:
            return f"Ошибка в аргументах функции '{func_name}': {e}"
        except Exception as e:
            return f"Критическая ошибка при выполнении '{func_name}': {e}"