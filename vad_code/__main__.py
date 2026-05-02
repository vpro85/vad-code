"""Главный модуль"""
import json
import re
from typing import Optional

import httpx

from vad_code.tools.file_tools import FileTools
from .config import PROJECT_ROOT, LM_STUDIO_URL, MODEL_NAME, MAX_ITERATIONS, MAX_HISTORY_MESSAGES, TIMEOUT


class AIOSBridge:
    """Класс, реализующий взаимодействие LLM-модели и ОС"""

    def __init__(self) -> None:
        # Системный промпт передается как первое сообщение в истории
        self.system_prompt = (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{PROJECT_ROOT}. "
            "Твоя задача - помогать пользователю анализировать и изменять код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            "1. list_files(directory) - возвращает список файлов в папке.\n"
            "2. read_file(filepath) - читает содержимое файла.\n"
            "3. write_file(filepath, content) - записывает текст в файл (перезаписывает).\n"
            "4. replace_in_file(filepath, old_text, new_text) - заменяет старый текст на новый в файле.\n\n"
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
        self.history: list[dict] = []
        self.file_tools = FileTools()
        # Реестр доступных функций: имя_в_промпте -> метод_класса
        self.tools = {
            "list_files": self.file_tools.list_files,
            "read_file": self.file_tools.read_file,
            "write_file": self.file_tools.write_file,
            "replace_in_file": self.file_tools.replace_in_file,
        }

    def _trim_history(self) -> None:
        """Обрезает историю, сохраняя первое сообщение пользователя (цель)"""
        if len(self.history) > MAX_HISTORY_MESSAGES:
            first_msg = self.history[0]
            recent_msgs = self.history[-(MAX_HISTORY_MESSAGES - 1):]
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
        """Парсит JSON-строку и вызывает функцию из реестра self.tools"""
        try:
            # Превращаем строку в Python-словарь
            call_data = json.loads(call_text)

            func_name = call_data.get("tool")
            args = call_data.get("arguments", {})

            if not func_name:
                return "Ошибка: В JSON не указано поле 'tool'."

            if func_name not in self.tools:
                return f"Ошибка: Функция '{func_name}' не поддерживается."

            # Вызываем функцию, распаковывая словарь аргументов как именованные параметры
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
            "model": MODEL_NAME,
            "messages": self._build_messages(),
            "temperature": 0.1,
        }

        try:
            response = httpx.post(LM_STUDIO_URL, json=payload, timeout=TIMEOUT)
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
        print(f"Подключение к {LM_STUDIO_URL}")
        print(f"Рабочая директория: {PROJECT_ROOT}\n")

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

            for i in range(MAX_ITERATIONS):
                self._trim_history()
                ai_response = self.query_llm()

                self.history.append({"role": "assistant", "content": ai_response})

                call_line = self._find_call_line(ai_response)

                if call_line:
                    print(f"🤖 AI вызывает инструмент... ({i + 1}/{MAX_ITERATIONS})")
                    print(f"   ↳ {call_line.strip()}")
                    observation = self.execute_call(call_line)
                    print(f"📝 Результат: {observation[:120]}...")
                    if observation is None:
                        print(f"\n🤖 AI: {ai_response}\n")
                        break

                    self.history.append({"role": "user", "content": f"OBSERVATION: {observation}"})
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
