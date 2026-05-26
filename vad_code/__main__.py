"""Точка входа"""
import argparse
import asyncio
from pathlib import Path

from vad_code.config import settings
from vad_code.core.agent import Agent
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_providers import create_provider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.tools.file_tools import FileTools, TOOL_REGISTRY
from vad_code.tools.git_tools import GitTools

VERSION = "0.3.0"


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="vad-code",
        description="🤖 AI-инженер для локальной разработки",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vad-code {VERSION}",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Путь к файлу конфигурации (.env)",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Рабочая директория проекта",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Название LLM-модели",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["openai", "ollama", "anthropic", "lm_studio"],
        help="Тип LLM-провайдера",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Максимальное количество итераций на запрос",
    )
    parser.add_argument(
        "--history-file",
        type=str,
        default=None,
        help="Путь к файлу для сохранения истории",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    """Запускает основной цикл агента."""
    # Применяем аргументы командной строки к настройкам
    if args.config:
        settings.model_config["env_file"] = args.config
    if args.project_root:
        settings.project_root = args.project_root
    if args.model:
        settings.llm_model = args.model
    if args.provider:
        settings.llm_provider = args.provider
    if args.max_iterations:
        settings.max_iterations = args.max_iterations

    log.info("🚀 AI-OS Bridge запущен (v%s).", VERSION)
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

    # Загрузка истории из файла
    history_file = Path(args.history_file) if args.history_file else None
    if history_file and history_file.exists():
        try:
            history_text = history_file.read_text(encoding="utf-8")
            log.info("📂 История загружена из %s", history_file)
        except Exception as e:
            log.warning("⚠️ Не удалось загрузить историю: %s", e)

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
                log.info("🧹 История очищена.")
                continue
            if user_input.lower() == "/stats":
                agent.print_stats()
                continue
            if user_input.lower() == "/help":
                log.info(
                    "\n📖 Доступные команды:\n"
                    "  /reset  - очистить историю\n"
                    "  /stats  - показать статистику сессии\n"
                    "  /help   - показать это сообщение\n"
                    "  exit/quit - выйти\n"
                )
                continue

            await agent.handle(user_input)
    finally:
        # Сохранение истории в файл
        if history_file:
            try:
                history_text = agent.memory.to_text()
                history_file.write_text(history_text, encoding="utf-8")
                log.info("💾 История сохранена в %s", history_file)
            except Exception as e:
                log.warning("⚠️ Не удалось сохранить историю: %s", e)

        await agent.close()
        log.info("Сетевые соединения закрыты.")


if __name__ == "__main__":
    try:
        args = parse_args()
        asyncio.run(run(args))
    except KeyboardInterrupt:
        log.info("\n\n👋 Выход из системы...")
    except Exception as e:
        log.error("❌ Критическая ошибка: %s", e)
        raise
