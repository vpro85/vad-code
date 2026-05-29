"""
Регистр инструментов.

Вынесен в отдельный модуль для избежания циклических импортов.
"""

from typing import Any

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}
