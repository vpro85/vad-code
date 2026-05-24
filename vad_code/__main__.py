"""Точка входа"""
import asyncio

from vad_code.config import settings
from vad_code.core.agent import Agent
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY


async def run() -> None:
    """Запускает основной цикл агента."""
    log.info("🚀 AI-OS Bridge (Local Mode) запущен.")
    log.info("Подключение к %s", settings.lm_studio_url)
    log.info("Рабочая директория: %s\n", settings.project_root)
    # 1. Создаем инфраструктурные компоненты
    llm_client = LLMClient()
    executor = ToolExecutor()
    tokenizer = Tokenizer()

    # 2. Настраиваем инструменты (теперь это делается на уровне конфигурации приложения)
    file_tools = FileTools()
    # Здесь мы вручную или через цикл регистрируем нужные методы
    for name, info in TOOL_REGISTRY.items():
        if hasattr(file_tools, name):
            method = getattr(file_tools, name)
            executor.register_tool(name, method, schema=info.get("schema"))

    agent = Agent(llm_client=llm_client, executor=executor, tokenizer=tokenizer)

    try:
        while True:
            try:
                user_input = input("Вы: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break
            if user_input.lower() == "/reset":
                agent.reset_history()
                continue

            await agent.handle(user_input)
    finally:
        # Гарантируем закрытие клиента httpx
        await agent.close()
        log.info("Сетевые соединения закрыты.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("\n\n👋 Выход из системы...")
