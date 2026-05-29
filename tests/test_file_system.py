from unittest.mock import patch

import pytest

from vad_code.infrastructure.file_system import FileSystemService


@pytest.fixture
def mock_settings(tmp_path):
    """
    Подменяет settings.project_root на временную директорию pytest,
    чтобы тесты не влияли на реальные файлы проекта.
    """
    with patch("vad_code.infrastructure.file_system.settings") as mock:
        mock.project_root = str(tmp_path)
        yield mock


@pytest.fixture
def fs_service(mock_settings):
    return FileSystemService()


def test_safe_path_valid(fs_service, tmp_path):
    # Создаем файл внутри временной директории
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    # Проверяем, что доступ к файлу внутри корня разрешен
    assert fs_service.safe_path("test.txt") == test_file.resolve()


def test_safe_path_invalid(fs_service):
    # Пытаемся выйти за пределы корня с помощью ../
    with pytest.raises(PermissionError) as excinfo:
        fs_service.safe_path("../../etc/passwd")
    assert "Доступ запрещен" in str(excinfo.value)


def test_read_text(fs_service, tmp_path):
    # Подготовка: создаем файл
    content = "Hello World"
    file_path = tmp_path / "hello.txt"
    file_path.write_text(content, encoding="utf-8")

    # Тест
    assert fs_service.read_text("hello.txt") == content


def test_write_text(fs_service, tmp_path):
    # Тест записи
    content = "New Content"
    fs_service.write_text("new.txt", content)

    assert (tmp_path / "new.txt").read_text() == content


def test_replace_text_success(fs_service, tmp_path):
    # Подготовка
    content = "The quick brown fox"
    file_path = tmp_path / "fox.txt"
    file_path.write_text(content, encoding="utf-8")

    # Тест замены
    fs_service.replace_text("fox.txt", "brown", "red")
    assert (tmp_path / "fox.txt").read_text() == "The quick red fox"


def test_replace_text_not_found(fs_service, tmp_path):
    # Подготовка
    content = "The quick brown fox"
    file_path = tmp_path / "fox.txt"
    file_path.write_text(content, encoding="utf-8")

    # Тест ошибки при отсутствии текста для замены
    with pytest.raises(ValueError) as excinfo:
        fs_service.replace_text("fox.txt", "blue", "green")
    assert "Текст для замены не найден" in str(excinfo.value)


def test_list_dir(fs_service, tmp_path):
    # Подготовка: создаем несколько файлов
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.py").touch()
    (tmp_path / "subdir").mkdir()

    files = fs_service.list_dir(".")
    assert "file1.txt" in files
    assert "file2.py" in files
    assert "subdir" in files
    assert len(files) == 3


def test_create_dir(fs_service, tmp_path):
    # Тест создания директории
    dir_name = "new_folder/subfolder"
    fs_service.create_dir(dir_name)
    assert (tmp_path / dir_name).is_dir()


def test_move_file(fs_service, tmp_path):
    # Подготовка: создаем файл
    src = "old_name.txt"
    dst = "new_name.txt"
    (tmp_path / src).write_text("content")

    # Тест перемещения
    fs_service.move_file(src, dst)
    assert (tmp_path / dst).exists()
    assert not (tmp_path / src).exists()


def test_delete_file_file(fs_service, tmp_path):
    # Подготовка: создаем файл
    filename = "to_delete.txt"
    (tmp_path / filename).touch()

    # Тест удаления файла
    fs_service.delete_file(filename)
    assert not (tmp_path / filename).exists()


def test_delete_file_dir(fs_service, tmp_path):
    # Подготовка: создаем директорию с файлом внутри
    dir_name = "to_delete_dir"
    dir_path = tmp_path / dir_name
    dir_path.mkdir()
    (dir_path / "inner.txt").touch()

    # Тест удаления директории
    fs_service.delete_file(dir_name)
    assert not dir_path.exists()


def test_copy_file(fs_service, tmp_path):
    # Подготовка: создаем файл
    src = "source.txt"
    dst = "destination.txt"
    content = "copy me"
    (tmp_path / src).write_text(content)

    # Тест копирования
    fs_service.copy_file(src, dst)
    assert (tmp_path / dst).exists()
    assert (tmp_path / dst).read_text() == content
    assert (tmp_path / src).exists()  # исходный файл остался


def test_copy_dir(fs_service, tmp_path):
    # Подготовка: создаем директорию с файлом
    src_dir = "source_dir"
    dst_dir = "dest_dir"
    src_path = tmp_path / src_dir
    src_path.mkdir()
    (src_path / "inner.txt").write_text("content")

    # Тест копирования директории
    fs_service.copy_file(src_dir, dst_dir)
    assert (tmp_path / dst_dir).is_dir()
    assert (tmp_path / dst_dir / "inner.txt").read_text() == "content"


def test_get_file_size(fs_service, tmp_path):
    # Подготовка: создаем файл
    filename = "sized.txt"
    content = "Hello World"
    (tmp_path / filename).write_text(content)

    # Тест получения размера файла
    size = fs_service.get_file_size(filename)
    assert size == len(content.encode("utf-8"))


def test_get_dir_size(fs_service, tmp_path):
    # Подготовка: создаем директорию с файлами
    dir_name = "sized_dir"
    dir_path = tmp_path / dir_name
    dir_path.mkdir()
    (dir_path / "file1.txt").write_text("aaa")
    (dir_path / "file2.txt").write_text("bbb")

    # Тест получения размера директории
    size = fs_service.get_file_size(dir_name)
    assert size == 6  # 3 + 3 байта


def test_find_files(fs_service, tmp_path):
    # Подготовка: создаем структуру файлов
    (tmp_path / "test_main.py").touch()
    (tmp_path / "test_utils.py").touch()
    (tmp_path / "app.py").touch()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "test_sub.py").touch()

    # Тест поиска
    files = fs_service.find_files("test_*.py")
    assert "test_main.py" in files
    assert "test_utils.py" in files
    assert "sub/test_sub.py" in files
    assert "app.py" not in files


def test_tail_file(fs_service, tmp_path):
    # Подготовка: создаем файл с несколькими строками
    filename = "log.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    # Тест чтения последних строк
    tail = fs_service.tail_file(filename, 3)
    assert "Line 8" in tail
    assert "Line 9" in tail
    assert "Line 10" in tail
    assert "Line 7" not in tail


def test_head_file(fs_service, tmp_path):
    # Подготовка: создаем файл с несколькими строками
    filename = "log.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    # Тест чтения первых строк
    head = fs_service.head_file(filename, 3)
    assert "Line 1" in head
    assert "Line 2" in head
    assert "Line 3" in head
    assert "Line 10" not in head


def test_get_file_info(fs_service, tmp_path):
    # Подготовка: создаем файл
    filename = "info.txt"
    content = "Hello World"
    (tmp_path / filename).write_text(content)

    # Тест получения информации
    info = fs_service.get_file_info(filename)
    assert info["name"] == "info.txt"
    assert info["is_file"] is True
    assert info["is_dir"] is False
    assert info["size"] == len(content.encode("utf-8"))
    assert "modified" in info
    assert "accessed" in info


def test_count_lines_file(fs_service, tmp_path):
    # Подготовка: создаем файл
    filename = "lines.txt"
    content = "\n".join(f"Line {i}" for i in range(1, 11))
    (tmp_path / filename).write_text(content)

    # Тест подсчета строк
    count = fs_service.count_lines(filename)
    assert count == 10


def test_count_lines_dir(fs_service, tmp_path):
    # Подготовка: создаем директорию с файлами
    dir_name = "code_dir"
    dir_path = tmp_path / dir_name
    dir_path.mkdir()
    (dir_path / "a.py").write_text("print('a')\nprint('b')")
    (dir_path / "b.py").write_text("x = 1\ny = 2\nz = 3")

    # Тест подсчета строк в директории
    count = fs_service.count_lines(dir_name)
    assert count == 5  # 2 + 3 строки
