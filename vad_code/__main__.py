"""Главный модуль"""
import re

from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY
from .config import settings


class AIOSBridge:
    """Класс, реализующий взаимодействие LLM-модели и ОС"""

    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self.file_tools = FileTools()
        self.tools_executor = ToolExecutor()

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

        self.history: list[dict] = []

    def _trim_history(self) -> None:
        # 1. Ограничение по количеству (как и было)
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent_msgs = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent_msgs

        # 2. НОВОЕ: Ограничение по общему объему текста (примерно)
        # Считаем общую длину всех сообщений в истории
        total_chars = sum(len(msg['content']) for msg in self.history)
        max_chars = 40000  # Примерный порог, чтобы не забить VRAM

        while total_chars > max_chars and len(self.history) > 2:
            # Удаляем второе сообщение (первое — это цель пользователя, его храним)
            removed = self.history.pop(1)
            total_chars -= len(removed['content'])

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
                ai_response = self.llm_client.complete(self._build_messages())

                self.history.append({"role": "assistant", "content": ai_response})

                call_line = self._find_call_line(ai_response)

                if call_line:
                    print(f"🤖 AI вызывает инструмент... ({i + 1}/{settings.max_iterations})")
                    print(f"   ↳ {call_line.strip()}")
                    observation = self.tools_executor.execute(call_line)
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
