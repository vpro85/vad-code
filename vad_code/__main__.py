"""Главный модуль"""
import json
import re
from typing import Optional

import httpx

from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY
from .config import settings


class AIOSBridge:
    """Класс, реализующий взаимодействие LLM-модели и ОС"""

    def __init__(self) -> None:
        self.file_tools = FileTools()
        self.tools = {}

        # 1. Динамически формируем список описаний для системного промпта
        tools_descriptions = []
        for name, info in TOOL_REGISTRY.items():
            tools_descriptions.append(f"{name}(...) - {info['description']}")

        tools_text = "\n".join([f"{i + 1}. {desc}" for i, desc in enumerate(tools_descriptions)])

        # 2. Формируем системный промпт (теперь он зависит от реестра)
        self.system_prompt = (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{settings.project_root}. "
            "Твоя задача - помогать пользователю анализировать и изменять код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            f"{tools_text}\n\n"
            "ПРОТОКОЛ ВЗАИМОДЕЙСТВИЯ:\n"
            "- Для вызова инструментов ОБЯЗАТЕЛЬНО используй блок кода JSON:\n"
            "```json\n"
            "{\n"
            '  "tool": "имя_функции",\n'
            '  "arguments": {"аргумент1": "значение1", "арting2": 123}\n'
            "}\n"
            "```\n"
            "- После каждого вызова ты получишь ответ в формате: OBSERVATION: [результат]\n"
            "- Когда у тебя будет достаточно информации для ответа пользователю, просто напиши финальный ответ.\n"
            "- Никогда не выдумывай содержимое файлов, используй только read_file."
        )
        # 3. Автоматически привязываем методы к экземпляру self.tools
        for name in TOOL_REGISTRY:
            if hasattr(self.file_tools, name):
                method = getattr(self.file_tools, name)
                self.tools[name] = method

        self.history: list[dict] = []

    def _trim_history(self) -> None:
        """Обрезает историю, сохраняя первое сообщение пользователя (цель)"""
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent_msgs = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent_msgs

    def _build_messages(self) -> list[dict]:
        """Собирает финальный список сообщений с system prompt в начале"""
        return [{"role": "system", "content": self.system_prompt}] + self.history

    def _find_call_line(self, ai_response: str) -> str | None:
        """Ищет JSON-блок в ответе модели"""
        # Ищем содержимое между ```json и ```
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, ai_response, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def execute_call(self, call_text: str) -> Optional[str]:
        """Парсит JSON-строку, валидирует аргументы через Pydantic и вызывает функцию"""
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
                        # Проверяем аргументы на соответствие схеме
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

    def query_llm(self) -> str:
        """Отправка запроса в LM Studio и получение ответа"""
        payload = {
            "model": settings.model_name,
            "messages": self._build_messages(),
            "temperature": 0.1,
        }

        try:
            response = httpx.post(settings.lm_studio_url, json=payload, timeout=settings.timeout)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка от LM Studio: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения с LM Studio: {e}"
        except (KeyError, IndexError) as e:
            return f"Ошибка: неожиданный формат ответа от LM Studio"

    def run(self) -> None:
        print("🚀 AI-OS Bridge (Local Mode) запущен.")
        print(f"Подключение к {settings.lm_studio_url}")
        print(f"Рабочая директория: {settings.project_root}\n")

        while True:
            try:
                user_input = input("Вы: ")
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                break

            self.history.append({"role": "user", "content": user_input})

            for i in range(settings.max_iterations):
                self._trim_history()
                ai_response = self.query_llm()

                self.history.append({"role": "assistant", "content": ai_response})

                call_line = self._find_call_line(ai_response)

                if call_line:
                    print(f"🤖 AI вызывает инструмент... ({i + 1}/{settings.max_iterations})")
                    print(f"   ↳ {call_line.strip()}")
                    observation = self.execute_call(call_line)
                    obs_text = observation if observation is not None else "Success"
                    print(f"📝 Результат: {obs_text[:120]}...")
                    self.history.append({"role": "user", "content": f"OBSERVATION: {obs_text}"})
                else:
                    print(f"\n🤖 AI: {ai_response}\n")
                    break
            else:
                print("\n⚠️ Достигнут лимит итераций.")


if __name__ == "__main__":
    try:
        bridge = AIOSBridge()
        bridge.run()
    except KeyboardInterrupt:
        print("\n\n👋 Выход из системы...")
