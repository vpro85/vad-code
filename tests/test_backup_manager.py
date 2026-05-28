"""Тесты для модуля backup_manager."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from vad_code.infrastructure.backup_manager import BackupManager


@pytest.fixture
def tmp_dir():
    """Создает временную директорию для тестов."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def backup_manager(tmp_dir):
    """Создает экземпляр BackupManager с тестовой директорией."""
    return BackupManager(backup_dir=os.path.join(tmp_dir, ".vad_backups"))


def test_create_backup_file(tmp_dir, backup_manager):
    """Проверяет создание бэкапа файла."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("original content")

    record = backup_manager.create_backup(str(test_file), operation="write")

    assert record is not None
    assert record.file_path == str(test_file.resolve())
    assert Path(record.backup_path).exists()
    assert backup_manager.undo_stack[-1] == record


def test_create_backup_nonexistent_file(tmp_dir, backup_manager):
    """Проверяет, что бэкап не создается для несуществующего файла."""
    nonexistent = Path(tmp_dir) / "no_such_file.txt"

    record = backup_manager.create_backup(str(nonexistent))

    assert record is None
    assert len(backup_manager.undo_stack) == 0


def test_undo_restores_file(tmp_dir, backup_manager):
    """Проверяет восстановление файла из бэкапа."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("original content")

    backup_manager.create_backup(str(test_file))

    # Изменяем файл
    test_file.write_text("modified content")

    # Отменяем изменение
    result = backup_manager.undo()

    assert "Отменено" in result
    assert test_file.read_text() == "original content"
    assert len(backup_manager.undo_stack) == 0
    assert len(backup_manager.redo_stack) == 1


def test_redo_reapplies_change(tmp_dir, backup_manager):
    """Проверяет повторение отмененного изменения."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("original content")

    backup_manager.create_backup(str(test_file))
    test_file.write_text("modified content")
    backup_manager.undo()

    # Файл должен быть восстановлен к оригиналу
    assert test_file.read_text() == "original content"

    # Повторяем изменение
    result = backup_manager.redo()

    assert "Повторено" in result
    assert test_file.read_text() == "modified content"
    assert len(backup_manager.undo_stack) == 1
    assert len(backup_manager.redo_stack) == 0


def test_undo_empty_stack(tmp_dir, backup_manager):
    """Проверяет поведение при пустом стеке Undo."""
    result = backup_manager.undo()
    assert "Нет изменений" in result


def test_redo_empty_stack(tmp_dir, backup_manager):
    """Проверяет поведение при пустом стеке Redo."""
    result = backup_manager.redo()
    assert "Нет изменений" in result


def test_max_undo_steps(tmp_dir, backup_manager):
    """Проверяет ограничение размера стека Undo."""
    backup_manager._max_undo_steps = 3

    for i in range(5):
        test_file = Path(tmp_dir) / f"file_{i}.txt"
        test_file.write_text(f"content {i}")
        backup_manager.create_backup(str(test_file))

    assert len(backup_manager.undo_stack) == 3


def test_clear_history(tmp_dir, backup_manager):
    """Проверяет очистку истории."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("content")
    backup_manager.create_backup(str(test_file))

    backup_manager.clear()

    assert len(backup_manager.undo_stack) == 0
    assert len(backup_manager.redo_stack) == 0


def test_get_history(tmp_dir, backup_manager):
    """Проверяет получение истории изменений."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("content")
    backup_manager.create_backup(str(test_file), operation="write")

    history = backup_manager.get_history()

    assert len(history) == 1
    assert history[0]["operation"] == "write"
    assert "test.txt" in history[0]["file"]


def test_backup_directory_created(tmp_dir, backup_manager):
    """Проверяет создание директории для бэкапов."""
    backup_dir = Path(tmp_dir) / ".vad_backups"
    assert not backup_dir.exists()

    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("content")
    backup_manager.create_backup(str(test_file))

    assert backup_dir.exists()
    assert backup_dir.is_dir()


def test_undo_deleted_file(tmp_dir, backup_manager):
    """Проверяет восстановление удаленного файла."""
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("content")

    backup_manager.create_backup(str(test_file), operation="delete")
    test_file.unlink()

    assert not test_file.exists()

    backup_manager.undo()

    assert test_file.exists()
    assert test_file.read_text() == "content"


def test_backup_directory(tmp_dir, backup_manager):
    """Проверяет бэкап директории."""
    test_dir = Path(tmp_dir) / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")

    record = backup_manager.create_backup(str(test_dir), operation="move")

    assert record is not None
    assert Path(record.backup_path).exists()
    assert Path(record.backup_path).is_dir()


def test_undo_restores_directory(tmp_dir, backup_manager):
    """Проверяет восстановление директории из бэкапа."""
    test_dir = Path(tmp_dir) / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")

    backup_manager.create_backup(str(test_dir))

    # Удаляем директорию
    shutil.rmtree(test_dir)

    # Отменяем
    backup_manager.undo()

    assert test_dir.exists()
    assert (test_dir / "file1.txt").read_text() == "content1"
