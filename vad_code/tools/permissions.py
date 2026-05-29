"""
Модуль управления разрешениями для инструментов.
"""

from enum import Enum
from typing import Callable, Any, Optional, Type
from pydantic import BaseModel


class ToolRiskLevel(Enum):
    """Уровни риска инструментов."""

    READ = "read"  # Только чтение (list_files, read_file, git_status)
    WRITE = "write"  # Изменение файлов (write_file, create_dir, git_commit)
    DANGEROUS = "dangerous"  # Опасные операции (delete_file, run_command)


class ToolPermission:
    """Класс для управления разрешениями."""

    def __init__(self, allowed_levels: Optional[list[ToolRiskLevel]] = None):
        """
        Инициализация разрешений.

        Args:
            allowed_levels: Список разрешенных уровней риска.
                           Если None, разрешены все уровни.
        """
        self.allowed_levels = allowed_levels

    def is_allowed(self, risk_level: ToolRiskLevel) -> bool:
        """Проверяет, разрешен ли данный уровень риска."""
        if self.allowed_levels is None:
            return True
        return risk_level in self.allowed_levels


# Глобальный менеджер разрешений
permission_manager = ToolPermission()


def register_tool(
    description: str,
    schema: Optional[Type[BaseModel]] = None,
    risk_level: ToolRiskLevel = ToolRiskLevel.READ,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для автоматической регистрации методов как инструментов AI.

    Args:
        description: Описание инструмента для LLM.
        schema: Pydantic-схема для валидации аргументов.
        risk_level: Уровень риска инструмента.
    """
    # Импортируем из отдельного модуля для избежания циклических импортов
    from vad_code.tools.registry import TOOL_REGISTRY

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        TOOL_REGISTRY[func.__name__] = {
            "description": description,
            "schema": schema,
            "func_name": func.__name__,
            "risk_level": risk_level,
        }
        return func

    return decorator
