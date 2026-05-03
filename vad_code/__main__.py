"""Точка входа"""
import asyncio

from vad_code.config import settings
from vad_code.core.agent import Agent
from vad_code.infrastructure.logger import log


async def run() -> None:
    log.info("🚀 AI-OS Bridge (Local Mode) запущен.")
    log.info(f"Подключение к {settings.lm_studio_url}")
    log.info(f"Рабочая директория: {settings.project_root}\n")

    agent = Agent()

    while True:
        try:
            user_input = input("Вы: ").strip()
        except EOFError:
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        await agent.handle(user_input)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("\n\n👋 Выход из системы...")
