"""Модуль инструментов."""
from typing import Any

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

# Импортируем подмодули, чтобы зарегистрировать инструменты
from vad_code.tools.file_system_tools import FileSystemTools  # noqa: F401
from vad_code.tools.search_tools import SearchTools  # noqa: F401
from vad_code.tools.info_tools import InfoTools  # noqa: F401
from vad_code.tools.command_tools import CommandTools  # noqa: F401
from vad_code.tools.bad_case_tools import BadCaseTools  # noqa: F401
from vad_code.tools.phase2_tools import Phase2Tools  # noqa: F401

# Импортируем фасад
from vad_code.tools.file_tools import FileTools  # noqa: F401
