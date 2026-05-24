from unittest.mock import patch

import pytest

from vad_code.tools.file_tools import FileTools


@pytest.fixture
def mock_settings(tmp_path):
    with patch('vad_code.infrastructure.file_system.settings') as mock:
        mock.project_root = str(tmp_path)
        yield mock


@pytest.fixture
def tools(mock_settings):
    return FileTools()


def test_list_files_success(tools, tmp_path):
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.py").touch()

    result = tools.list_files(".")
    assert "file1.txt" in result
    assert "file2.py" in result


def test_list_files_error(tools):
    # Передаем путь, который вызовет PermissionError в safe_path
    result = tools.list_files("../../etc")
    assert "Ошибка при чтении списка файлов" in result


def test_list_tree(tools, tmp_path):
    # Создаем структуру:
    # root/
    #   dir1/
    #     file1.txt
    #   file2.py
    #   .git/ (должен быть проигнорирован)
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "file1.txt").touch()
    (tmp_path / "file2.py").touch()
    (tmp_path / ".git").mkdir()

    result = tools.list_tree(".", depth=2)
    assert "📁 ." in result
    assert "├── 📁 dir1" in result or "└── 📁 dir1" in result
    assert "📄 file1.txt" in result
    assert "📄 file2.py" in result
    assert ".git" not in result


def test_read_file_cache(tools, tmp_path):
    filename = "test.txt"
    content = "Hello Cache"
    (tmp_path / filename).write_text(content)

    # Первый раз - чтение из файла
    res1 = tools.read_file(filename)
    assert content in res1
    assert "[кэш]" not in res1

    # Второй раз - чтение из кэша
    res2 = tools.read_file(filename)
    assert content in res2
    assert "[кэш]" in res2


def test_write_file_success(tools, tmp_path):
    filename = "write_test.txt"
    content = "New Content"
    # Создаем файл для проверки перезаписи
    (tmp_path / filename).write_text("Old Content")

    result = tools.write_file(filename, content)
    assert "успешно записан" in result
    assert (tmp_path / filename).read_text() == content
    # Бэкапы больше не создаются
    assert not (tmp_path / f"{filename}.bak").exists()


def test_replace_in_file(tools, tmp_path):
    filename = "replace.txt"
    (tmp_path / filename).write_text("Hello World")

    # Успешная замена
    result = tools.replace_in_file(filename, "World", "AI")
    assert "успешно обновлен" in result
    assert (tmp_path / filename).read_text() == "Hello AI"

    # Ошибка: текст не найден
    result = tools.replace_in_file(filename, "Missing", "Something")
    assert "Ошибка при обновлении файла" in result


def test_search_in_files(tools, tmp_path):
    # Создаем файлы для поиска
    (tmp_path / "a.py").write_text("print('hello')\nprint('world')")
    (tmp_path / "b.py").write_text("def main(): pass")

    # Поиск строки
    result = tools.search_in_files("hello")
    assert "a.py:1: print('hello')" in result

    # Поиск regex
    result = tools.search_in_files("print\(.*\)")
    assert "a.py:1" in result
    assert "a.py:2" in result

    # Ничего не найдено
    result = tools.search_in_files("nonexistent")
    assert "не найдено" in result


def test_read_file_lines(tools, tmp_path):
    filename = "lines.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4"
    (tmp_path / filename).write_text(content)

    # Чтение диапазона
    result = tools.read_file_lines(filename, 2, 3)
    assert "Строки 2-3" in result
    assert "Line 2\nLine 3" in result

    # Файл не найден
    result = tools.read_file_lines("missing.txt", 1, 10)
    assert "Ошибка: Файл missing.txt не найден" in result


def test_create_dir(tools, tmp_path):
    dir_name = "new_dir"
    result = tools.create_dir(dir_name)
    assert "успешно создана" in result
    assert (tmp_path / dir_name).is_dir()


def test_move_file(tools, tmp_path):
    src = "old.txt"
    dst = "new.txt"
    (tmp_path / src).write_text("data")

    result = tools.move_file(src, dst)
    assert "успешно перемещен" in result
    assert (tmp_path / dst).exists()
    assert not (tmp_path / src).exists()


def test_delete_file(tools, tmp_path):
    filename = "del.txt"
    (tmp_path / filename).touch()

    result = tools.delete_file(filename)
    assert "успешно удален" in result
    assert not (tmp_path / filename).exists()


def test_run_command_allowed(tools, tmp_path):
    # Создаем файл для pytest
    (tmp_path / "test_dummy.py").write_text("def test_pass(): assert True")

    result = tools.run_command("pytest test_dummy.py")
    assert "Код выхода: 0" in result


def test_run_command_forbidden(tools):
    result = tools.run_command("rm -rf /")
    assert "запрещена" in result
