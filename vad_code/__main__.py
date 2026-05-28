"""Точка входа"""
import argparse
import asyncio
from pathlib import Path

from vad_code.config import settings
from vad_code.core.agent import Agent
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_providers import create_provider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.metrics import format_metrics, reset_metrics
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.tools import FileTools, TOOL_REGISTRY
from vad_code.tools.git_tools import GitTools
from vad_code.tools.permissions import permission_manager, ToolRiskLevel

VERSION = "0.4.0"


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

    # Настройка разрешений
    allowed_levels_str = settings.allowed_tool_risk_levels.lower()
    if allowed_levels_str == "all":
        allowed_levels = None
    else:
        allowed_levels = []
        for level_str in allowed_levels_str.split(","):
            level_str = level_str.strip()
            if level_str == "read":
                allowed_levels.append(ToolRiskLevel.READ)
            elif level_str == "write":
                allowed_levels.append(ToolRiskLevel.WRITE)
            elif level_str == "dangerous":
                allowed_levels.append(ToolRiskLevel.DANGEROUS)
        if not allowed_levels:
            allowed_levels = None  # Если строка пустая, разрешаем всё

    permission_manager.allowed_levels = allowed_levels

    log.info("🚀 AI-OS Bridge запущен (v%s).", VERSION)
    log.info("LLM-провайдер: %s", settings.llm_provider)
    log.info("Модель: %s", settings.llm_model)
    log.info("Рабочая директория: %s", settings.project_root)
    log.info("Разрешенные уровни риска: %s\n", settings.allowed_tool_risk_levels)

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
            executor.register_tool(name, method, schema=info.get("schema"), metadata=info)
        elif hasattr(git_tools, name):
            method = getattr(git_tools, name)
            executor.register_tool(name, method, schema=info.get("schema"), metadata=info)

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
                reset_metrics()
                log.info("🧹 История и метрики сброшены.")
                continue
            if user_input.lower() == "/undo":
                result = agent.undo()
                log.info("%s", result)
                continue
            if user_input.lower() == "/redo":
                result = agent.redo()
                log.info("%s", result)
                continue
            if user_input.lower() == "/history":
                history = agent.get_change_history()
                if not history:
                    log.info("📜 История изменений пуста.")
                else:
                    log.info("📜 История изменений:")
                    for i, h in enumerate(history, 1):
                        log.info("  %d. %s -> %s", i, h["operation"], h["file"])
                continue
            if user_input.lower() == "/audit":
                audit_log = agent.get_audit_records()
                log.info("📝 Журнал аудита:\n%s", audit_log)
                continue
            if user_input.lower() == "/audit-stats":
                audit_stats = agent.get_audit_stats()
                log.info("%s", audit_stats)
                continue
            if user_input.lower() == "/metrics":
                metrics = format_metrics()
                log.info("%s", metrics)
                continue
            if user_input.lower() == "/stats":
                agent.print_stats()
                continue
            if user_input.lower() == "/help":
                log.info(
                    "\n📖 Доступные команды:\n"
                    "  /reset      - очистить историю и метрики\n"
                    "  /undo       - отменить последнее изменение файла\n"
                    "  /redo       - повторить отмененное изменение\n"
                    "  /history    - показать историю изменений файлов\n"
                    "  /audit      - показать журнал аудита действий\n"
                    "  /audit-stats - показать статистику вызовов инструментов\n"
                    "  /metrics    - показать метрики сессии (время, токены, инструменты)\n"
                    "  /stats      - показать статистику сессии\n"
                    "  /help       - показать это сообщение\n"
                    "  exit/quit   - выйти\n"
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
