"""Главный модуль"""
import os
import re
from typing import Optional

import httpx

# =================== Настройки ===================
PROJECT_ROOT = os.getcwd()
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-31b"
MAX_ITERATIONS = 50
MAX_HISTORY_MESSAGES = 20
TIMEOUT = 20 * 60
ALLOWED_FUNCTIONS = {"list_files", "read_file"}


# =================================================


class AIOSBridge:
    """Класс, реализующий взаимодействие LLM-модели и ОС"""

    def __init__(self) -> None:
        # Системный промпт передается как первое сообщение в истории
        self.system_prompt = (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{PROJECT_ROOT}. "
            "Твоя задача - помогать пользователю анализировать код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            "1. list_files(directory) - возвращает список файлов в папке.\n"
            "2. read_file(filepath) - читает содержимое файла.\n\n"
            "ПРОТОКОЛ ВЗАИМОДЕЙСТВИЯ:\n"
            "- Если тебе нужно использовать инструмент, используй один из следующих форматов:\n"
            "  CALL: list_files(directory='путь/к/папке')\n"
            "  CALL: read_file(filepath='путь/к/файлу')\n"
            "- После этого ты получишь ответ в формате: OBSERVATION: [результат]\n"
            "- Когда у тебя будет достаточно информации для ответа "
            "пользователю, просто напиши финальный ответ.\n"
            "- Никогда не выдумывай содержимое файлов, используй только read_file."
            "ПРАВИЛА:\n"
            "- Вызов инструмента пишется СТРОГО на отдельной строке, начиная с первого символа:\n"
            "  CALL: list_files(directory='.')\n"
            "- Никакого другого текста на этой строке быть не должно.\n"
            "- Не используй CALL: в примерах или объяснениях.\n"
            "- Если инструмент не нужен — просто пиши финальный ответ без CALL.\n"
        )
        # Здесь мы храним всю историю переписки для контекста локальной модели
        # self.history = [
        #     {"role": "system", "content": self.system_prompt},
        # ]
        self.history: list[dict] = []

    def _trim_history(self) -> None:
        """Обрезает историю, чтобы не переполнить контекстное окно модели"""
        if len(self.history) > MAX_HISTORY_MESSAGES:
            self.history = self.history[-MAX_HISTORY_MESSAGES:]

    def _build_messages(self) -> list[dict]:
        """Собирает финальный список сообщений с system prompt в начале"""
        return [{"role": "system", "content": self.system_prompt}] + self.history

    def safe_path(self, path: str) -> str:
        """Обеспечивает работу внутри разрешенной директории"""
        abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if not abs_path.startswith(PROJECT_ROOT):
            raise PermissionError(
                "Доступ запрещен: путь находится вне рабочей директории."
            )
        return abs_path

    # --- Инструменты (TOOLBOX) ---
    def list_files(self, directory: str = ".") -> str:
        try:
            path = self.safe_path(directory)
            files = os.listdir(path)
            return f"Файлы в {directory}: {', '.join(files)}"
        except Exception as e:
            return f"Ошибка при чтении списка файлов: {str(e)}"

    def read_file(self, filepath: str) -> str:
        try:
            path = self.safe_path(filepath)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                return f"Содержимое файла {filepath}:\n---\n{content}\n---"
        except Exception as e:
            return f"Ошибка при чтении файла: {str(e)}"

    def _find_call_line(self, ai_response: str) -> str | None:
        """Возвращает строку с вызовом только если она начинается с CALL:"""
        for line in ai_response.splitlines():
            stripped = line.strip()
            # Строка должна НАЧИНАТЬСЯ с CALL:, а не содержать его где-то внутри
            if stripped.startswith("CALL:"):
                return stripped
        return None

    def execute_call(self, call_text: str) -> Optional[str]:
        """Парсит строку вида CALL: func(key='value') и вызывает нужную функцию"""
        func_match = re.search(r"CALL:\s*(\w+)\(", call_text)
        if not func_match:
            return None  # None - не валидный вызов, игнорируем

        func_name = func_match.group(1)
        if func_name not in ALLOWED_FUNCTIONS:
            # Не сообщаем модели об ошибке - просто игнорируем
            return None

        # Извлекаем все аргументы вида key='value' или key="value"
        args: dict[str, str] = dict(
            re.findall(r"(\w+)=['\"]([^'\"]*)['\"]", call_text)
        )

        if func_name == "list_files":
            return self.list_files(args.get("directory", "."))
        elif func_name == "read_file":
            filepath = args.get("filepath")
            if not filepath:
                return "Ошибка: функция read_file требует аргумент filepath."
            return self.read_file(filepath)
        else:
            return f"Ошибка: Функция {func_name} не существует."

    def query_llm(self) -> str:
        """Отправка запроса в LM Studio и получение ответа"""
        payload = {
            "model": MODEL_NAME,
            "messages": self._build_messages(),
            "temperature": 0.1,  # Низкая температура для строгого следования протоколу CALL
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

            # Добавляем сообщение пользователя в историю
            self.history.append({"role": "user", "content": user_input})

            for i in range(MAX_ITERATIONS):
                self._trim_history()
                ai_response = self.query_llm()

                # Сохраним ответ ИИ в историю, чтобы он помнил свои рассуждения
                self.history.append({"role": "assistant", "content": ai_response})

                call_line = self._find_call_line(ai_response)

                if call_line:
                    print(f"🤖 AI вызывает инструмент... ({i + 1}/{MAX_ITERATIONS})")
                    print(f"   ↳ {call_line.strip()}")
                    observation = self.execute_call(call_line)
                    print(f"📝 Результат: {observation[:120]}...")
                    if observation is None:
                        # Ложное срабатывание — считаем это финальным ответом
                        print(f"\n🤖 AI: {ai_response}\n")
                        break

                    # Добавляем результат выполнения функции в историю как сообщение от пользователя/системы
                    self.history.append({"role": "user", "content": f"OBSERVATION: {observation}"})
                else:
                    print(f"\n🤖 AI: {ai_response}\n")
                    break
            else:
                print("\n⚠️ Достигнут лимит итераций.")


if __name__ == '__main__':
    try:
        bridge = AIOSBridge()
        bridge.run()
    except KeyboardInterrupt:
        print('\n\n👋 Выход из системы...')
