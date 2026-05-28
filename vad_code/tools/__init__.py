"""Модуль инструментов."""

from typing import Any

from vad_code.tools.file_system_tools import FileSystemTools
from vad_code.tools.search_tools import SearchTools
from vad_code.tools.info_tools import InfoTools
from vad_code.tools.command_tools import CommandTools
from vad_code.tools.bad_case_tools import BadCaseTools
from vad_code.tools.phase2_tools import Phase2Tools
from vad_code.tools.file_tools import FileTools

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

__all__ = [
    "FileSystemTools",
    "SearchTools",
    "InfoTools",
    "CommandTools",
    "BadCaseTools",
    "Phase2Tools",
    "FileTools",
    "TOOL_REGISTRY",
]
