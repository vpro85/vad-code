"""
Регистр инструментов.

Вынесен в отдельный модуль для избежания циклических импортов.
"""

from typing import Any

from vad_code.tools.permissions import ToolRiskLevel
from vad_code.tools.schemas import (
    ConfigCreateDefaultSchema,
    ConfigGetSchema,
    ConfigSaveSchema,
    ConfigSetSchema,
    MemoryAddSchema,
    MemoryClearSchema,
    MemoryGetContextSchema,
    MemoryGetSchema,
    MemorySearchSchema,
    MemoryStatsSchema,
)

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # --- Проектная память ---
    "memory_add": {
        "description": "Добавляет запись в проектную память (сохраняет знания между сессиями)",
        "schema": MemoryAddSchema,
        "risk_level": ToolRiskLevel.WRITE,
    },
    "memory_get": {
        "description": "Получает запись из проектной памяти по ключу",
        "schema": MemoryGetSchema,
        "risk_level": ToolRiskLevel.READ,
    },
    "memory_search": {
        "description": "Ищет записи в проектной памяти по тексту",
        "schema": MemorySearchSchema,
        "risk_level": ToolRiskLevel.READ,
    },
    "memory_get_context": {
        "description": "Возвращает контекст из проектной памяти для включения в промпт",
        "schema": MemoryGetContextSchema,
        "risk_level": ToolRiskLevel.READ,
    },
    "memory_stats": {
        "description": "Возвращает статистику проектной памяти",
        "schema": MemoryStatsSchema,
        "risk_level": ToolRiskLevel.READ,
    },
    "memory_clear": {
        "description": "Очищает проектную память",
        "schema": MemoryClearSchema,
        "risk_level": ToolRiskLevel.DANGEROUS,
    },
    # --- Конфигурация проекта ---
    "config_get": {
        "description": "Возвращает текущую конфигурацию проекта",
        "schema": ConfigGetSchema,
        "risk_level": ToolRiskLevel.READ,
    },
    "config_set": {
        "description": "Устанавливает значение в конфигурации проекта",
        "schema": ConfigSetSchema,
        "risk_level": ToolRiskLevel.WRITE,
    },
    "config_create_default": {
        "description": "Создает файл конфигурации vad-code.json по умолчанию",
        "schema": ConfigCreateDefaultSchema,
        "risk_level": ToolRiskLevel.WRITE,
    },
    "config_save": {
        "description": "Сохраняет текущую конфигурацию проекта",
        "schema": ConfigSaveSchema,
        "risk_level": ToolRiskLevel.WRITE,
    },
}
