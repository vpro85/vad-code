"""
Инструменты для работы с проектной памятью и конфигурацией.
"""

from typing import Any

from vad_code.core.project_config import ProjectConfigManager
from vad_code.core.project_memory import ProjectMemory


def get_project_memory(project_root: str) -> ProjectMemory:
    """Получает или создает объект проектной памяти."""
    return ProjectMemory(project_root)


def get_project_config(project_root: str) -> ProjectConfigManager:
    """Получает или создает менеджер конфигурации проекта."""
    return ProjectConfigManager(project_root)


# ------------------------------------------------------------------
# Инструменты проектной памяти
# ------------------------------------------------------------------

def memory_add(
    key: str,
    value: str,
    category: str,
    confidence: float = 1.0,
) -> str:
    """
    Добавляет запись в проектную память.

    :param key: Уникальный ключ записи.
    :param value: Значение (текст записи).
    :param category: Категория: architecture, convention, decision, fact.
    :param confidence: Уверенность (0.0 - 1.0).
    :return: Статус операции.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    memory.add(key=key, value=value, category=category, confidence=confidence)
    memory.save()
    return f"✅ Запись '{key}' добавлена в проектную память."


def memory_get(key: str) -> str:
    """
    Получает запись из проектной памяти по ключу.

    :param key: Ключ записи.
    :return: Содержимое записи или сообщение об отсутствии.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    entry = memory.get(key)
    if entry:
        return (
            f"📝 Запись '{key}':\n"
            f"  Категория: {entry.category}\n"
            f"  Уверенность: {entry.confidence}\n"
            f"  Значение: {entry.value}"
        )
    return f"❌ Запись '{key}' не найдена в проектной памяти."


def memory_search(query: str) -> str:
    """
    Ищет записи в проектной памяти по тексту.

    :param query: Текст для поиска.
    :return: Найденные записи.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    results = memory.search(query)
    if not results:
        return f"❌ Записи по запросу '{query}' не найдены."

    lines = [f"🔍 Найдено {len(results)} записей по запросу '{query}':"]
    for entry in results:
        lines.append(f"  - [{entry.category}] {entry.key}: {entry.value[:100]}")
    return "\n".join(lines)


def memory_get_context() -> str:
    """
    Возвращает контекст из проектной памяти для включения в промпт.

    :return: Форматированный контекст проекта.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    return memory.get_context_prompt()


def memory_stats() -> str:
    """
    Возвращает статистику проектной памяти.

    :return: Статистика.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    stats = memory.get_stats()
    lines = [
        "📊 Статистика проектной памяти:",
        f"  Всего записей: {stats['total_entries']}",
        f"  Файл: {stats['memory_file']}",
    ]
    if stats["categories"]:
        lines.append("  По категориям:")
        for cat, count in stats["categories"].items():
            lines.append(f"    - {cat}: {count}")
    return "\n".join(lines)


def memory_clear() -> str:
    """
    Очищает проектную память.

    :return: Статус операции.
    """
    from vad_code.config import settings

    memory = get_project_memory(settings.project_root)
    memory.clear()
    return "🧹 Проектная память очищена."


# ------------------------------------------------------------------
# Инструменты конфигурации проекта
# ------------------------------------------------------------------

def config_get() -> str:
    """
    Возвращает текущую конфигурацию проекта.

    :return: Содержимое конфигурации.
    """
    from vad_code.config import settings

    manager = get_project_config(settings.project_root)
    config_dict = manager.get_effective_config()
    lines = ["📋 Конфигурация проекта:"]
    for key, value in config_dict.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def config_set(key: str, value: str) -> str:
    """
    Устанавливает значение в конфигурации проекта.

    :param key: Ключ конфигурации.
    :param value: Новое значение.
    :return: Статус операции.
    """
    from vad_code.config import settings

    manager = get_project_config(settings.project_root)
    valid_keys = {
        "name", "description", "python_version", "test_framework",
        "code_style", "enable_multi_agent", "max_iterations",
        "allowed_tools", "excluded_paths", "custom_instructions",
    }
    if key not in valid_keys:
        return f"❌ Неизвестный ключ конфигурации: '{key}'. Доступные: {', '.join(sorted(valid_keys))}"

    # Преобразование типов
    parsed_value: Any = value
    if key == "enable_multi_agent":
        parsed_value = value.lower() in ("true", "1", "yes")
    elif key == "max_iterations":
        parsed_value = int(value)
    elif key in ("allowed_tools", "excluded_paths"):
        parsed_value = [v.strip() for v in value.split(",") if v.strip()]

    setattr(manager.config, key, parsed_value)
    manager.save()
    return f"✅ Конфигурация '{key}' установлена: {parsed_value}"


def config_create_default() -> str:
    """
    Создает файл конфигурации по умолчанию.

    :return: Статус операции.
    """
    from vad_code.config import settings

    manager = get_project_config(settings.project_root)
    manager.create_default()
    return "✅ Файл конфигурации vad-code.json создан."


def config_save() -> str:
    """
    Сохраняет текущую конфигурацию.

    :return: Статус операции.
    """
    from vad_code.config import settings

    manager = get_project_config(settings.project_root)
    manager.save()
    return f"💾 Конфигурация сохранена: {manager.config_file}"


# ------------------------------------------------------------------
# Метаданные инструментов
# ------------------------------------------------------------------

PROJECT_TOOLS_METADATA: dict[str, dict[str, Any]] = {
    # Память
    "memory_add": {
        "description": "Добавляет запись в проектную память (сохраняет знания между сессиями)",
        "risk_level": "write",
    },
    "memory_get": {
        "description": "Получает запись из проектной памяти по ключу",
        "risk_level": "read",
    },
    "memory_search": {
        "description": "Ищет записи в проектной памяти по тексту",
        "risk_level": "read",
    },
    "memory_get_context": {
        "description": "Возвращает контекст из проектной памяти для включения в промпт",
        "risk_level": "read",
    },
    "memory_stats": {
        "description": "Возвращает статистику проектной памяти",
        "risk_level": "read",
    },
    "memory_clear": {
        "description": "Очищает проектную память",
        "risk_level": "dangerous",
    },
    # Конфигурация
    "config_get": {
        "description": "Возвращает текущую конфигурацию проекта",
        "risk_level": "read",
    },
    "config_set": {
        "description": "Устанавливает значение в конфигурации проекта",
        "risk_level": "write",
    },
    "config_create_default": {
        "description": "Создает файл конфигурации vad-code.json по умолчанию",
        "risk_level": "write",
    },
    "config_save": {
        "description": "Сохраняет текущую конфигурацию проекта",
        "risk_level": "write",
    },
}

PROJECT_TOOLS = {
    "memory_add": memory_add,
    "memory_get": memory_get,
    "memory_search": memory_search,
    "memory_get_context": memory_get_context,
    "memory_stats": memory_stats,
    "memory_clear": memory_clear,
    "config_get": config_get,
    "config_set": config_set,
    "config_create_default": config_create_default,
    "config_save": config_save,
}
