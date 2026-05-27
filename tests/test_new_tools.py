"""
Тесты для новых инструментов run_tests и format_code.
"""
import pytest
from unittest.mock import patch, MagicMock
from vad_code.tools.file_tools import FileTools


@pytest.fixture
def tools(tmp_path):
    with patch('vad_code.tools.file_system_tools.FileSystemService') as mock_fs:
        mock_fs.return_value.root = tmp_path
        t = FileTools()
        t._fs_tools.fs = mock_fs.return_value
        t._command_tools.fs = mock_fs.return_value
        return t


def test_run_tests_success(tools, tmp_path):
    """Проверяет успешный запуск тестов."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1 passed in 0.1s",
            stderr=""
        )
        result = tools.run_tests(path="tests/")
        assert "Код выхода: 0" in result
        assert "1 passed" in result
        mock_run.assert_called_once()


def test_run_tests_failure(tools, tmp_path):
    """Проверяет запуск тестов с ошибками."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="1 failed in 0.5s",
            stderr="AssertionError: 1 != 2"
        )
        result = tools.run_tests(path="tests/")
        assert "Код выхода: 1" in result
        assert "1 failed" in result


def test_run_tests_timeout(tools, tmp_path):
    """Проверяет таймаут при запуске тестов."""
    import subprocess
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=["pytest"], timeout=10)):
        result = tools.run_tests(path="tests/", timeout=10)
        assert "Ошибка" in result


def test_format_code_success(tools, tmp_path):
    """Проверяет успешное форматирование."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1 file reformatted",
            stderr=""
        )
        result = tools.format_code(path="src/", tool="black")
        assert "Код выхода: 0" in result
        assert "1 file reformatted" in result


def test_format_code_check_only(tools, tmp_path):
    """Проверяет режим только проверки."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        result = tools.format_code(path="src/", tool="black", check_only=True)
        assert "Код уже отформатирован" in result


def test_format_code_invalid_tool(tools, tmp_path):
    """Проверяет ошибку при неизвестном инструменте."""
    result = tools.format_code(path="src/", tool="unknown_tool")
    assert "неизвестный инструмент" in result


def test_format_code_not_installed(tools, tmp_path):
    """Проверяет ошибку при отсутствии инструмента."""
    with patch('subprocess.run', side_effect=FileNotFoundError()):
        result = tools.format_code(path="src/", tool="black")
        assert "не установлен" in result
