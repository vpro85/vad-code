"""Главный модуль"""
import os
import re

import httpx

# =================== Настройки ===================
PROJECT_ROOT = os.getcwd()
LM_STUDIO_URL = "http://127.0.0.1:1234"
MODEL_NAME = "google/gemma-4-31b"
MAX_ITERATIONS = 5


# =================================================


class AIOSBridge:
    """Класс, реализующий взаимодействие LLM-модели и ОС"""

    def __init__(self) -> None:
        # Системный промпт передается как первое сообщение в истории
        self.system_prompt = (
            "Ты - AI-инженер, имеющий доступ к файловой системе в директории: "
            f"{PROJECT_ROOT}."
            "Твоя задача - помогать пользователю анализировать код.\n\n"
            "ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
            "1. list_files(directory) - возвращает список файлов в папке.\n"
            "2. read_file(filepath) - читает содержимое файла.\n\n"
            "ПРОТОКОЛ ВЗАИМОДЕЙСТВИЯ:\n"
            "- Если тебе нужно использовать инструмент, напиши строго в "
            "формате: CALL: "
            "function_name(arg='value')\n"
            "- После этого ты получишь ответ в формате: OBSERVATION: "
            "[результат]\n"
            "- Когда у тебя будет достаточно информации для ответа "
            "пользователю, просто напиши финальный ответ.\n"
            "- Никогда не выдумывай содержимое файлов, используй только "
            "read_file."
        )
        # Здесь мы храним всю историю переписки для контекста локальной модели
        self.history = [
            {"role": "system", "content": self.system_prompt},
        ]

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

    def execute_call(self, call_text: str) -> str:
        match = re.search(r"CALL:\s*(\w+)\((?:.*'([^']*)')?\)", call_text)
        if not match:
            return "Ошибка: Неверный формат вызова CALL."

        func_name, arg = match.groups()
        arg = arg or "."

        if func_name == "list_files":
            return self.list_files(arg)
        elif func_name == "read_file":
            return self.read_file(arg)
        else:
            return f"Ошибка: Функция {func_name} не существует."

    def query_lim(self) -> str:
        """Отправка запроса в LM Studio и получение ответа"""
        payload = {
            "model": MODEL_NAME,
            "messages": self.history,
            "temperature": 0.1,  # Низкая температура для строгого следования протоколу CALL
        }

        try:
            response = httpx.post(LM_STUDIO_URL, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Ошибка связи с LM Studio: {str(e)}"

    def run(self) -> None:
        print("🚀 AI-OS Bridge (Local Mode запущен.")
        print(f"Подключение к {LM_STUDIO_URL}")
        print(f"Рабочая директория: {PROJECT_ROOT}\n")

        while True:
            user_input = input("Вы: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Добавляем сообщение пользователя в историю
            self.history.append({"role": "system", "content": user_input})

            for i in range(MAX_ITERATIONS):
                # Получаем ответы от локальной модели
                ai_response = self.query_lim()

                # Сохраним ответ ИИ в историю, чтобы он помнил свои рассуждения
                self.history.append({"role": "system", "content": ai_response})

                if "CALL" in ai_response:
                    print(f"🤖 AI вызывает инструмент... ({i + 1}/{MAX_ITERATIONS})")

                    # Извлекаем строку с вызовом
                    call_line = [line for line in ai_response.split("\n") if "CALL:" in line][0]
                    observation = self.execute_call(call_line)

                    print(f"📝 Результат: {observation[:100]}...")

                    # Добавляем результат выполнения функции в историю как сообщение от пользователя/системы
                    self.history.append({"role": "system", "content": f"OBSERVATION: {observation}"})
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
