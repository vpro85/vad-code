"""Smoke-тест: проверка базовых импортов при запуске приложения."""


def test_import_project_tools():
    """Проверяет, что PROJECT_TOOLS импортируется из vad_code.tools."""
    from vad_code.tools import PROJECT_TOOLS

    assert PROJECT_TOOLS is not None
    assert isinstance(PROJECT_TOOLS, dict)
    assert len(PROJECT_TOOLS) > 0


def test_import_tool_registry():
    """Проверяет, что TOOL_REGISTRY импортируется из vad_code.tools."""
    from vad_code.tools import TOOL_REGISTRY

    assert TOOL_REGISTRY is not None
    assert isinstance(TOOL_REGISTRY, dict)


def test_import_file_tools():
    """Проверяет, что FileTools импортируется из vad_code.tools."""
    from vad_code.tools import FileTools

    assert FileTools is not None


def test_project_tools_has_expected_keys():
    """Проверяет, что PROJECT_TOOLS содержит ожидаемые инструменты."""
    from vad_code.tools import PROJECT_TOOLS

    expected_tools = [
        "memory_add",
        "memory_get",
        "memory_search",
        "memory_get_context",
        "memory_stats",
        "memory_clear",
        "config_get",
        "config_set",
        "config_create_default",
        "config_save",
    ]
    for tool_name in expected_tools:
        assert tool_name in PROJECT_TOOLS, f"Инструмент '{tool_name}' отсутствует в PROJECT_TOOLS"


def test_main_module_imports():
    """Проверяет, что все импорты из __main__.py работают."""
    from vad_code.tools import FileTools, PROJECT_TOOLS, TOOL_REGISTRY
    from vad_code.core.agent import Agent
    from vad_code.core.executor import ToolExecutor
    from vad_code.infrastructure.tokenizer import Tokenizer

    assert FileTools is not None
    assert PROJECT_TOOLS is not None
    assert TOOL_REGISTRY is not None
    assert Agent is not None
    assert ToolExecutor is not None
    assert Tokenizer is not None
