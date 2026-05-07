import pytest
from unittest.mock import patch
from pathlib import Path
from vad_code.tools.file_tools import FileTools


@pytest.fixture
def mock_settings(tmp_path):
    with patch('vad_code.infrastructure.file_system.settings') as mock:
        mock.project_root = str(tmp_path)
        yield mock


@pytest.fixture
def tools(mock_settings):
    return FileTools()


def test_write_file_disk_full(tools, tmp_path):
    """Тест ошибки 'Диск заполнен' (OSError 28) при записи файла."""
    filename = "full_disk.txt"
    content = "New Content"
    (tmp_path / filename).write_text("Initial content")

    with patch("pathlib.Path.write_text") as mock_write:
        mock_write.side_effect = OSError(28, "No space left on device")

        result = tools.write_file(filename, content)
        assert "Ошибка при записи файла" in result
        assert "No space left on device" in result


def test_write_file_permission_denied(tools, tmp_path):
    """Тест ошибки 'Доступ запрещен' (PermissionError) при записи файла."""
    filename = "no_permission.txt"
    content = "New Content"
    (tmp_path / filename).write_text("Initial content")

    with patch("pathlib.Path.write_text") as mock_write:
        mock_write.side_effect = PermissionError(13, "Permission denied")

        result = tools.write_file(filename, content)
        assert "Ошибка при записи файла" in result
        assert "Permission denied" in result


def test_write_file_leaves_backup_on_failure(tools, tmp_path):
    """Проверка, что при ошибке записи остается .bak файл (анализ побочного эффекта)."""
    filename = "backup_test.txt"
    content = "New Content"
    (tmp_path / filename).write_text("Original Content")

    with patch("pathlib.Path.write_text") as mock_write:
        mock_write.side_effect = OSError(28, "No space left on device")

        tools.write_file(filename, content)

        backup_file = tmp_path / f"{filename}.bak"
        assert backup_file.exists(), "Backup file should exist even if write failed"


def test_create_dir_permission_denied(tools, tmp_path):
    """Тест ошибки при создании директории (например, нет прав)."""
    dir_name = "forbidden_dir"
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        mock_mkdir.side_effect = PermissionError(13, "Permission denied")

        result = tools.create_dir(dir_name)
        assert "Ошибка при создании директории" in result
        assert "Permission denied" in result


def test_read_file_not_found(tools):
    """Тест ошибки 'Файл не найден' при чтении."""
    result = tools.read_file("non_existent_file.txt")
    assert "Ошибка: Файл non_existent_file.txt не найден" in result