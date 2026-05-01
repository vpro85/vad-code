"""Главный модуль"""
import os
import re
from pathlib import Path
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
        self.history: list[dict] = []
        # Реестр доступных функций: имя_в_промпте -> метод_класса
        self.tools = {
            "list_files": self.list_files,
            "read_file": self.read_file,
        }

    def _trim_history(self) -> None:
        """Обрезает историю, сохраняя первое сообщение пользователя (цель)"""
        if len(self.history) > MAX_HISTORY_MESSAGES:
            # Сохраняем самое первое сообщение (инструкция/запрос пользователя)
            # и последние N-1 сообщений для контекста текущего шага
            first_msg = self.history[0]
            recent_msgs = self.history[-(MAX_HISTORY_MESSAGES - 1):]
            self.history = [first_msg] + recent_msgs

    def _build_messages(self) -> list[dict]:
        """Собирает финальный список сообщений с system prompt в начале"""
        return [{"role": "system", "content": self.system_prompt}] + self.history

    def safe_path(self, path: str) -> Path:
        """Обеспечивает работу внутри разрешенной директории с использованием pathlib"""
        root = Path(PROJECT_ROOT).resolve()
        # Создаем абсолютный путь, объединяя корень и переданный путь
        target = (root / path).resolve()

        if not target.is_relative_to(root):
            raise PermissionError(
                f"Доступ запрещен: путь {target} находится вне рабочей директории {root}."
            )
        return target

    # --- Инструменты (TOOLBOX) ---
    def list_files(self, directory: str = ".") -> str:
        try:
            path = self.safe_path(directory)
            files = path.iterdir()  # Используем pathlib
            file_list = [f.name for f in files]
            return f"Файлы в {directory}: {', '.join(file_list)}"
        except Exception as e:
            return f"Ошибка при чтении списка файлов: {str(e)}"

    def read_file(self, filepath: str) -> str:
        try:
            path = self.safe_path(filepath)
            content = path.read_text(encoding="utf-8")  # Упрощенное чтение через pathlib
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
        """Парсит строку CALL и вызывает функцию из реестра self.tools"""
        func_match = re.search(r"CALL:\s*(\w+)\(", call_text)
        if not func_match:
            return None

        func_name = func_match.group(1)
        if func_name not in self.tools:
            return None  # Игнорируем неизвестные функции

        # Извлекаем аргументы в словарь
        args = dict(re.findall(r"(\w+)=['\"]([^'\"]*)['\"]", call_text))

        try:
            # Вызываем функцию из реестра, передавая ей распакованные аргументы
            return self.tools[func_name](**args)
        except TypeError as e:
            return f"Ошибка в аргументах функции {func_name}: {e}"
        except Exception as e:
            return f"Критическая ошибка при выполнении {func_name}: {e}"

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
