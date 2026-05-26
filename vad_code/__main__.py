"""Точка входа"""
import asyncio

from vad_code.config import settings
from vad_code.core.agent import Agent
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_providers import create_provider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY
from vad_code.tools.git_tools import GitTools


async def run() -> None:
    """Запускает основной цикл агента."""
    log.info("🚀 AI-OS Bridge запущен.")
    log.info("LLM-провайдер: %s", settings.llm_provider)
    log.info("Модель: %s", settings.llm_model)
    log.info("Рабочая директория: %s\n", settings.project_root)

    # 1. Создаем инфраструктурные компоненты
    llm_provider = create_provider(
        provider_type=settings.llm_provider,
        url=settings.llm_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout=settings.timeout,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    executor = ToolExecutor()
    tokenizer = Tokenizer()

    # 2. Настраиваем инструменты
    file_tools = FileTools()
    git_tools = GitTools()
    for name, info in TOOL_REGISTRY.items():
        if hasattr(file_tools, name):
            method = getattr(file_tools, name)
            executor.register_tool(name, method, schema=info.get("schema"))
        elif hasattr(git_tools, name):
            method = getattr(git_tools, name)
            executor.register_tool(name, method, schema=info.get("schema"))

    agent = Agent(llm_client=llm_provider, executor=executor, tokenizer=tokenizer)

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
        await agent.close()
        log.info("Сетевые соединения закрыты.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("\n\n👋 Выход из системы...")
