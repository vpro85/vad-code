"""Тесты для инструментов Фазы 2."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from vad_code.tools.phase2_tools import Phase2Tools


@pytest.fixture
def phase2_tools(tmp_path):
    """Фикстура для Phase2Tools с временной директорией."""
    from vad_code.infrastructure.file_system import FileSystemService
    fs = FileSystemService()
    fs.root = tmp_path
    tools = Phase2Tools()
    tools.fs = fs
    return tools


class TestPackageManagement:
    """Тесты управления пакетами."""

    def test_uninstall_package_success(self, phase2_tools):
        """Тест успешного удаления пакета."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Successfully uninstalled test-package",
                stderr="",
            )
            result = phase2_tools.uninstall_package("test-package")
            assert "успешно удалён" in result
            mock_run.assert_called_once()

    def test_uninstall_package_error(self, phase2_tools):
        """Тест ошибки при удалении пакета."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Package not found",
            )
            result = phase2_tools.uninstall_package("nonexistent")
            assert "Код выхода: 1" in result

    def test_list_packages(self, phase2_tools):
        """Тест списка пакетов."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Package\tVersion\ntest\t1.0.0",
                stderr="",
            )
            result = phase2_tools.list_packages()
            assert "test" in result

    def test_list_packages_with_filter(self, phase2_tools):
        """Тест фильтрации пакетов."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Package\tVersion\nnumpy\t1.21.0\npandas\t1.3.0\ntest\t1.0.0",
                stderr="",
            )
            result = phase2_tools.list_packages(filter_pattern="numpy")
            assert "numpy" in result
            assert "pandas" not in result

    def test_update_package(self, phase2_tools):
        """Тест обновления пакета."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Successfully installed test-2.0.0",
                stderr="",
            )
            result = phase2_tools.update_package(package="test")
            assert "успешно обновлены" in result


class TestRunLinter:
    """Тесты запуска линтеров."""

    def test_run_linter_pylint(self, phase2_tools):
        """Тест запуска pylint."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Your code has been rated at 10.00/10",
                stderr="",
            )
            result = phase2_tools.run_linter(tool="pylint", path=".")
            assert "rated" in result

    def test_run_linter_unknown_tool(self, phase2_tools):
        """Тест неизвестного линтера."""
        result = phase2_tools.run_linter(tool="unknown")
        assert "неизвестный линтер" in result

    def test_run_linter_with_args(self, phase2_tools):
        """Тест линтера с дополнительными аргументами."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="OK",
                stderr="",
            )
            phase2_tools.run_linter(tool="flake8", path=".", args="--max-line-length=120")
            assert "--max-line-length=120" in str(mock_run.call_args)


class TestSearchAndReplace:
    """Тесты поиска и замены."""

    def test_search_and_replace_dry_run(self, phase2_tools, tmp_path):
        """Тест dry-run режима."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old_text = 'hello'\nold_text = 'world'")

        result = phase2_tools.search_and_replace(
            search_pattern="old_text",
            replace_with="new_text",
            path=".",
            dry_run=True,
        )

        assert "DRY RUN" in result
        assert "2 замен" in result
        # Файл не должен измениться
        assert "old_text" in test_file.read_text()

    def test_search_and_replace_actual(self, phase2_tools, tmp_path):
        """Тест реальной замены."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old_text = 'hello'")

        result = phase2_tools.search_and_replace(
            search_pattern="old_text",
            replace_with="new_text",
            path=".",
            dry_run=False,
        )

        assert "Файлы изменены" in result
        assert "new_text" in test_file.read_text()

    def test_search_and_replace_no_matches(self, phase2_tools, tmp_path):
        """Тест отсутствия совпадений."""
        test_file = tmp_path / "test.py"
        test_file.write_text("some content")

        result = phase2_tools.search_and_replace(
            search_pattern="nonexistent",
            replace_with="replacement",
            path=".",
        )

        assert "Не найдено совпадений" in result


class TestFindDuplicates:
    """Тесты поиска дубликатов."""

    def test_find_duplicates(self, phase2_tools, tmp_path):
        """Тест поиска дублирующегося кода."""
        # Создаем файлы с одинаковым кодом
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        duplicate_code = "x = 1000\ny = 2000\nz = 3000\na = 4000\nb = 5000"
        file1.write_text(duplicate_code)
        file2.write_text(duplicate_code)

        result = phase2_tools.find_duplicates(path=".", min_lines=3)
        assert "дублирующихся блоков" in result

    def test_find_duplicates_no_duplicates(self, phase2_tools, tmp_path):
        """Тест отсутствия дубликатов."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("unique_code_1")
        file2.write_text("unique_code_2")

        result = phase2_tools.find_duplicates(path=".", min_lines=3)
        assert "не найдено" in result


class TestAnalyzeComplexity:
    """Тесты анализа сложности."""

    def test_analyze_complexity_simple(self, phase2_tools, tmp_path):
        """Тест анализа простой функции."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("def simple():\n    return 1\n")

        result = phase2_tools.analyze_complexity(path=".", threshold=10)
        assert "не найдено" in result

    def test_analyze_complexity_complex(self, phase2_tools, tmp_path):
        """Тест анализа сложной функции."""
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
def complex_func(a, b, c):
    if a:
        if b:
            if c:
                for i in range(10):
                    while i > 0:
                        i -= 1
    elif a:
        pass
    else:
        try:
            pass
        except:
            pass
    return True
""")

        result = phase2_tools.analyze_complexity(path=".", threshold=5)
        assert "complex_func" in result


class TestFindCodeSmells:
    """Тесты поиска запахов кода."""

    def test_find_code_smells_long_function(self, phase2_tools, tmp_path):
        """Тест обнаружения длинной функции."""
        test_file = tmp_path / "smelly.py"
        # Функция > 50 строк
        lines = ["def long_func():"]
        for i in range(55):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x54")
        test_file.write_text("\n".join(lines))

        result = phase2_tools.find_code_smells(path=".")
        assert "слишком длинная" in result

    def test_find_code_smells_many_args(self, phase2_tools, tmp_path):
        """Тест обнаружения функции с множеством аргументов."""
        test_file = tmp_path / "smelly.py"
        test_file.write_text("def many_args(a, b, c, d, e, f):\n    pass\n")

        result = phase2_tools.find_code_smells(path=".")
        assert "слишком много аргументов" in result


class TestGenerateDocstring:
    """Тесты генерации docstring."""

    def test_generate_docstring(self, phase2_tools, tmp_path):
        """Тест генерации docstring."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(arg1, arg2):\n    pass\n")

        result = phase2_tools.generate_docstring(path="test.py", style="google")
        assert "Сгенерировано" in result
        content = test_file.read_text()
        assert "'''" in content
        assert "Args:" in content

    def test_generate_docstring_already_exists(self, phase2_tools, tmp_path):
        """Тест когда docstring уже есть."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func():\n    '''Docstring.'''\n    pass\n")

        result = phase2_tools.generate_docstring(path="test.py")
        assert "уже имеют docstring" in result


class TestAnalyzeDependencies:
    """Тесты анализа зависимостей."""

    def test_analyze_dependencies(self, phase2_tools, tmp_path):
        """Тест анализа зависимостей."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nimport sys\nfrom pathlib import Path\n")

        result = phase2_tools.analyze_dependencies(path=".")
        assert "os" in result
        assert "sys" in result
        assert "pathlib" in result


class TestFindUnusedImports:
    """Тесты поиска неиспользуемых импортов."""

    def test_find_unused_imports(self, phase2_tools, tmp_path):
        """Тест поиска неиспользуемых импортов."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nimport sys\nprint('hello')\n")

        result = phase2_tools.find_unused_imports(path=".")
        assert "os" in result
        assert "sys" in result

    def test_find_unused_imports_none(self, phase2_tools, tmp_path):
        """Тест когда все импорты используются."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nprint(os.getcwd())\n")

        result = phase2_tools.find_unused_imports(path=".")
        assert "не найдено" in result


class TestListProcesses:
    """Тесты работы с процессами."""

    def test_list_processes(self, phase2_tools):
        """Тест списка процессов."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="USER\tPID\nroot\t1",
                stderr="",
            )
            result = phase2_tools.list_processes()
            assert "PID" in result


class TestKillProcess:
    """Тесты завершения процессов."""

    def test_kill_process_not_found(self, phase2_tools):
        """Тест завершения несуществующего процесса."""
        result = phase2_tools.kill_process(pid=999999)
        assert "не найден" in result or "Ошибка" in result


class TestRunBackgroundTask:
    """Тесты фоновых задач."""

    def test_run_background_task(self, phase2_tools):
        """Тест запуска фоновой задачи."""
        with patch("vad_code.infrastructure.command_security.command_validator.validate") as mock_validate:
            mock_validate.return_value = (True, "")
            result = phase2_tools.run_background_task(command="echo hello")
            assert "Фоновая задача запущена" in result

    def test_run_background_task_unsafe(self, phase2_tools):
        """Тест блокировки опасной команды."""
        with patch("vad_code.infrastructure.command_security.command_validator.validate") as mock_validate:
            mock_validate.return_value = (False, "Unsafe command")
            result = phase2_tools.run_background_task(command="rm -rf /")
            assert "Ошибка безопасности" in result
