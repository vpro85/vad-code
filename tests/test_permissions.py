"""Тесты для системы разрешений инструментов."""

import pytest
import json5
from unittest.mock import patch

from vad_code.core.executor import ToolExecutor
from vad_code.tools.permissions import ToolPermission, ToolRiskLevel


@pytest.fixture
def permission_manager():
    manager = ToolPermission()
    manager.allowed_levels = None  # Сброс к разрешению всего
    return manager


@pytest.fixture
def executor():
    return ToolExecutor()


class TestPermissionManager:
    """Тесты класса PermissionManager."""

    def test_is_allowed_when_all_allowed(self, permission_manager):
        """Когда allowed_levels=None, все уровни разрешены."""
        assert permission_manager.is_allowed(ToolRiskLevel.READ) is True
        assert permission_manager.is_allowed(ToolRiskLevel.WRITE) is True
        assert permission_manager.is_allowed(ToolRiskLevel.DANGEROUS) is True

    def test_is_allowed_read_only(self, permission_manager):
        """Когда разрешен только READ, WRITE и DANGEROUS запрещены."""
        permission_manager.allowed_levels = [ToolRiskLevel.READ]
        assert permission_manager.is_allowed(ToolRiskLevel.READ) is True
        assert permission_manager.is_allowed(ToolRiskLevel.WRITE) is False
        assert permission_manager.is_allowed(ToolRiskLevel.DANGEROUS) is False

    def test_is_allowed_read_and_write(self, permission_manager):
        """Когда разрешены READ и WRITE, DANGEROUS запрещен."""
        permission_manager.allowed_levels = [ToolRiskLevel.READ, ToolRiskLevel.WRITE]
        assert permission_manager.is_allowed(ToolRiskLevel.READ) is True
        assert permission_manager.is_allowed(ToolRiskLevel.WRITE) is True
        assert permission_manager.is_allowed(ToolRiskLevel.DANGEROUS) is False

    def test_is_allowed_empty_list(self, permission_manager):
        """Когда список пуст, ничего не разрешено."""
        permission_manager.allowed_levels = []
        assert permission_manager.is_allowed(ToolRiskLevel.READ) is False
        assert permission_manager.is_allowed(ToolRiskLevel.WRITE) is False
        assert permission_manager.is_allowed(ToolRiskLevel.DANGEROUS) is False


class TestExecutorPermissions:
    """Тесты интеграции разрешений с ToolExecutor."""

    @pytest.mark.anyio
    async def test_execute_tool_allowed(self, executor):
        """Инструмент с READ разрешен по умолчанию."""

        def read_tool():
            return "read data"

        executor.register_tool(
            "read_tool", read_tool, metadata={"risk_level": ToolRiskLevel.READ}
        )
        call_text = json5.dumps({"tool": "read_tool", "arguments": {}})
        result = await executor.execute(call_text)
        assert result == "read data"

    @pytest.mark.anyio
    async def test_execute_tool_denied(self, executor):
        """Инструмент с DANGEROUS запрещен, если не разрешен."""

        def dangerous_tool():
            return "dangerous action"

        executor.register_tool(
            "dangerous_tool",
            dangerous_tool,
            metadata={"risk_level": ToolRiskLevel.DANGEROUS},
        )

        with patch.object(
            executor,
            "metadata",
            {"dangerous_tool": {"risk_level": ToolRiskLevel.DANGEROUS}},
        ):
            # Глобальный permission_manager по умолчанию разрешает всё
            # Нужно явно ограничить
            from vad_code.tools.permissions import permission_manager

            original = permission_manager.allowed_levels
            permission_manager.allowed_levels = [ToolRiskLevel.READ]
            try:
                call_text = json5.dumps({"tool": "dangerous_tool", "arguments": {}})
                result = await executor.execute(call_text)
                assert "Доступ запрещен" in result
                assert "dangerous" in result
                assert "💡" in result
            finally:
                permission_manager.allowed_levels = original

    @pytest.mark.anyio
    async def test_execute_tool_no_metadata_defaults_to_read(self, executor):
        """Инструмент без метаданных считается READ."""

        def simple_tool():
            return "simple"

        executor.register_tool("simple_tool", simple_tool)
        call_text = json5.dumps({"tool": "simple_tool", "arguments": {}})
        result = await executor.execute(call_text)
        assert result == "simple"

    @pytest.mark.anyio
    async def test_execute_tool_write_allowed(self, executor):
        """Инструмент с WRITE разрешен, если WRITE в списке."""

        def write_tool():
            return "written"

        executor.register_tool(
            "write_tool", write_tool, metadata={"risk_level": ToolRiskLevel.WRITE}
        )

        from vad_code.tools.permissions import permission_manager

        original = permission_manager.allowed_levels
        permission_manager.allowed_levels = [ToolRiskLevel.READ, ToolRiskLevel.WRITE]
        try:
            call_text = json5.dumps({"tool": "write_tool", "arguments": {}})
            result = await executor.execute(call_text)
            assert result == "written"
        finally:
            permission_manager.allowed_levels = original

    @pytest.mark.anyio
    async def test_execute_tool_write_denied(self, executor):
        """Инструмент с WRITE запрещен, если только READ разрешен."""

        def write_tool():
            return "written"

        executor.register_tool(
            "write_tool", write_tool, metadata={"risk_level": ToolRiskLevel.WRITE}
        )

        from vad_code.tools.permissions import permission_manager

        original = permission_manager.allowed_levels
        permission_manager.allowed_levels = [ToolRiskLevel.READ]
        try:
            call_text = json5.dumps({"tool": "write_tool", "arguments": {}})
            result = await executor.execute(call_text)
            assert "Доступ запрещен" in result
            assert "💡" in result
        finally:
            permission_manager.allowed_levels = original
