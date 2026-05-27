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
    result = tools.search_in_files(r"print\(.*\)")
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


def test_copy_file(tools, tmp_path):
    src = "source.txt"
    dst = "dest.txt"
    content = "copy me"
    (tmp_path / src).write_text(content)

    result = tools.copy_file(src, dst)
    assert "успешно скопирован" in result
    assert (tmp_path / dst).exists()
    assert (tmp_path / dst).read_text() == content
    assert (tmp_path / src).exists()  # исходный файл остался


def test_copy_dir(tools, tmp_path):
    src_dir = "src_dir"
    dst_dir = "dst_dir"
    src_path = tmp_path / src_dir
    src_path.mkdir()
    (src_path / "inner.txt").write_text("content")

    result = tools.copy_file(src_dir, dst_dir)
    assert "успешно скопирован" in result
    assert (tmp_path / dst_dir).is_dir()
    assert (tmp_path / dst_dir / "inner.txt").read_text() == "content"


def test_get_file_size(tools, tmp_path):
    filename = "sized.txt"
    content = "Hello World"
    (tmp_path / filename).write_text(content)

    result = tools.get_file_size(filename)
    assert "Размер" in result
    assert "bytes" in result or "байт" in result


def test_get_dir_size(tools, tmp_path):
    dir_name = "sized_dir"
    dir_path = tmp_path / dir_name
    dir_path.mkdir()
    (dir_path / "file1.txt").write_text("aaa")
    (dir_path / "file2.txt").write_text("bbb")

    result = tools.get_file_size(dir_name)
    assert "Размер" in result
    assert "6" in result  # 3 + 3 байта


def test_find_files(tools, tmp_path):
    # Подготовка: создаем структуру файлов
    (tmp_path / "test_main.py").touch()
    (tmp_path / "test_utils.py").touch()
    (tmp_path / "app.py").touch()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "test_sub.py").touch()

    result = tools.find_files("test_*.py")
    assert "test_main.py" in result
    assert "test_utils.py" in result
    assert "sub/test_sub.py" in result
    assert "app.py" not in result


def test_tail_file(tools, tmp_path):
    filename = "log.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    result = tools.tail_file(filename, 3)
    assert "Последние 3 строк" in result
    assert "Line 8" in result
    assert "Line 10" in result
    assert "Line 7" not in result


def test_head_file(tools, tmp_path):
    filename = "log.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    result = tools.head_file(filename, 3)
    assert "Первые 3 строк" in result
    assert "Line 1" in result
    assert "Line 3" in result
    assert "Line 10" not in result


def test_get_file_info(tools, tmp_path):
    filename = "info.txt"
    content = "Hello World"
    (tmp_path / filename).write_text(content)

    result = tools.get_file_info(filename)
    assert "info.txt" in result
    assert "Файл" in result
    assert "11 байт" in result


def test_count_lines_file(tools, tmp_path):
    filename = "lines.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    result = tools.count_lines(filename)
    assert "Количество строк" in result
    assert "10" in result


def test_count_lines_dir(tools, tmp_path):
    dir_name = "code_dir"
    dir_path = tmp_path / dir_name
    dir_path.mkdir()
    (dir_path / "a.py").write_text("print('a')\nprint('b')")
    (dir_path / "b.py").write_text("x = 1\ny = 2\nz = 3")

    result = tools.count_lines(dir_name)
    assert "Количество строк" in result
    assert "5" in result


def test_lru_cache_eviction(tools, tmp_path):
    """Проверяет, что LRU-кэш ограничивает размер и удаляет старые элементы."""
    from vad_code.infrastructure.cache import SimpleLRUCache

    # Создаем кэш с лимитом 3 элемента
    cache = SimpleLRUCache(max_size=3)

    # Добавляем 3 элемента
    cache.put("file1.txt", "content1")
    cache.put("file2.txt", "content2")
    cache.put("file3.txt", "content3")

    # Все 3 элемента должны быть в кэше
    found, val = cache.get("file1.txt")
    assert found and val == "content1"
    found, val = cache.get("file2.txt")
    assert found and val == "content2"
    found, val = cache.get("file3.txt")
    assert found and val == "content3"

    # Добавляем 4-й элемент — самый старый (file1.txt) должен быть удален
    cache.put("file4.txt", "content4")

    # file1.txt больше не в кэше (был самым старым)
    found, val = cache.get("file1.txt")
    assert not found

    # Остальные элементы на месте
    found, val = cache.get("file2.txt")
    assert found and val == "content2"
    found, val = cache.get("file3.txt")
    assert found and val == "content3"
    found, val = cache.get("file4.txt")
    assert found and val == "content4"


def test_lru_cache_access_updates_order(tools, tmp_path):
    """Проверяет, что доступ к элементу обновляет его порядок (LRU)."""
    from vad_code.infrastructure.cache import SimpleLRUCache

    cache = SimpleLRUCache(max_size=3)

    # Добавляем 3 элемента
    cache.put("file1.txt", "content1")
    cache.put("file2.txt", "content2")
    cache.put("file3.txt", "content3")

    # Доступ к file1.txt — он становится самым свежим
    cache.get("file1.txt")

    # Добавляем 4-й элемент — теперь file2.txt должен быть удален (самый старый)
    cache.put("file4.txt", "content4")

    # file2.txt удален
    found, _ = cache.get("file2.txt")
    assert not found

    # file1.txt остался (был недавно доступен)
    found, val = cache.get("file1.txt")
    assert found and val == "content1"


def test_file_tools_cache_integration(tools, tmp_path):
    """Интеграционный тест: проверяет, что кэш FileTools не растет бесконечно."""
    # Создаем 60 файлов (больше, чем лимит кэша в 50)
    for i in range(60):
        filename = f"file_{i}.txt"
        content = f"content_{i}"
        (tmp_path / filename).write_text(content)

    # Читаем все файлы — кэш должен содержать только последние 50
    for i in range(60):
        tools.read_file(f"file_{i}.txt")

    # Проверяем, что кэш не содержит больше 50 элементов
    # Кэш теперь инкапсулирован внутри FileSystemTools
    assert len(tools._fs_tools._cache.cache) <= 50

    # Первые 10 файлов должны быть вытеснены из кэша
    for i in range(10):
        found, _ = tools._fs_tools._cache.get(f"file_{i}.txt")
        assert not found, f"file_{i}.txt должен быть вытеснен из кэша"

    # Последние файлы должны быть в кэше
    for i in range(40, 60):
        found, val = tools._fs_tools._cache.get(f"file_{i}.txt")
        assert found and val == f"content_{i}"


def test_grep_in_file(tools, tmp_path):
    """Проверяет поиск по содержимому одного файла."""
    filename = "grep_test.txt"
    content = "Line 1: hello\nLine 2: world\nLine 3: hello again\nLine 4: end"
    (tmp_path / filename).write_text(content)

    # Поиск строки без контекста
    result = tools.grep_in_file(filename, "hello", context_lines=0)
    assert "Line 1: hello" in result
    assert "Line 3: hello again" in result
    assert "Line 2: world" not in result

    # Поиск с контекстом
    result = tools.grep_in_file(filename, "world", context_lines=1)
    assert "Line 1: hello" in result
    assert "Line 2: world" in result
    assert "Line 3: hello again" in result

    # Ничего не найдено
    result = tools.grep_in_file(filename, "missing")
    assert "не найдено" in result

    # Файл не найден
    result = tools.grep_in_file("missing.txt", "hello")
    assert "не найден" in result


def test_get_project_stats(tools, tmp_path):
    """Проверяет получение статистики проекта."""
    # Создаем структуру файлов
    (tmp_path / "a.py").write_text("print('a')\nprint('b')")
    (tmp_path / "b.py").write_text("x = 1")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "c.py").write_text("y = 2\nz = 3\nw = 4")

    result = tools.get_project_stats(".", "*.py")
    assert "Статистика проекта" in result
    assert "Файлов (*.py): 3" in result
    assert "Всего строк: 6" in result
    assert "Общий размер" in result
