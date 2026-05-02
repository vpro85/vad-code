"""Главный модуль"""
import ast
from pathlib import Path
from typing import Optional

from vad_code.tools.file_tools import FileTools
from .config import PROJECT_ROOT, LM_STUDIO_URL, MODEL_NAME, MAX_ITERATIONS, MAX_HISTORY_MESSAGES, TIMEOUT
import httpx


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
            "- Ты можешь использовать как именованные (keyword), так и позиционные аргументы для краткости.\n"
            "- Пример вызова: `CALL: list_files('.')` или `CALL: read_file(filepath='path/to/file')`\n"
            "- Если тебе нужно использовать инструмент, используй формат:\n"
            "  CALL: <function_name>(<args>)\n"
            "- После этого ты получишь ответ в формате: OBSERVATION: [результат]\n"
            "- Когда у тебя будет достаточно информации для ответа "
            "пользователю, просто напиши финальный ответ.\n"
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
        """Возвращает полный текст вызова, даже если он занимает несколько строк"""
        if "CALL:" not in ai_response:
            return None

        start_idx = ai_response.find("CALL:")
        end_idx = ai_response.rfind(")")

        if end_idx == -1 or end_idx < start_idx:
            return None

        return ai_response[start_idx: end_idx + 1]

    def execute_call(self, call_text: str) -> Optional[str]:
        """Парсит строку CALL с использованием AST и вызывает функцию из реестра self.tools"""
        code = call_text.replace("CALL:", "").strip()

        try:
            tree = ast.parse(code, mode="eval")
            call_node = tree.body

            if not isinstance(call_node, ast.Call):
                return None

            if not isinstance(call_node.func, ast.Name):
                return None

            func_name = call_node.func.id
            if func_name not in self.tools:
                return f"Ошибка: Функция {func_name} не поддерживается."

            # Извлекаем позиционные аргументы
            args = [ast.literal_eval(arg) for arg in call_node.args]

            # Извлекаем именованные аргументы (keywords)
            kwargs = {}
            for kw in call_node.keywords:
                kwargs[kw.arg] = ast.literal_eval(kw.value)

            return self.tools[func_name](*args, **kwargs)

        except SyntaxError:
            return "Ошибка: Некорректный синтаксис вызова функции."
        except ValueError as e:
            return f"Ошибка в значениях аргументов: {e}"
        except TypeError as e:
            return f"Ошибка в аргументах функции {func_name}: {e}"
        except Exception as e:
            return f"Критическая ошибка при выполнении {func_name}: {e}"

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
