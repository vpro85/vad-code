"""
Модуль инструментов для работы с файловой системой.

Этот модуль служит точкой входа для всех инструментов.
Логика разбита на отдельные классы для лучшей поддерживаемости.
"""

from vad_code.tools.file_system_tools import FileSystemTools
from vad_code.tools.search_tools import SearchTools
from vad_code.tools.info_tools import InfoTools
from vad_code.tools.command_tools import CommandTools
from vad_code.tools.bad_case_tools import BadCaseTools


class FileTools:
    """
    Фасад для всех инструментов файловой системы.

    Агрегирует функциональность из отдельных модулей.
    """

    def __init__(self) -> None:
        self._fs_tools = FileSystemTools()
        self._search_tools = SearchTools()
        self._info_tools = InfoTools()
        self._command_tools = CommandTools()
        self._bad_case_tools = BadCaseTools()

    # --- Делегирование методов ---

    # FileSystemTools
    def list_files(self, path: str = ".") -> str:
        """Возвращает список файлов в указанной директории."""
        return self._fs_tools.list_files(path)  # type: ignore[no-any-return]

    def list_tree(self, path: str = ".", depth: int = 2) -> str:
        """Возвращает дерево файлов в указанной директории."""
        return self._fs_tools.list_tree(path, depth)  # type: ignore[no-any-return]

    def read_file(self, path: str) -> str:
        """Читает содержимое файла."""
        return self._fs_tools.read_file(path)  # type: ignore[no-any-return]

    def write_file(self, path: str, content: str) -> str:
        """Записывает содержимое в файл."""
        return self._fs_tools.write_file(path, content)  # type: ignore[no-any-return]

    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        """Заменяет текст в файле."""
        return self._fs_tools.replace_in_file(path, old_text, new_text)  # type: ignore[no-any-return]

    def read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        """Читает диапазон строк из файла."""
        return self._fs_tools.read_file_lines(path, start_line, end_line)  # type: ignore[no-any-return]

    def create_dir(self, path: str) -> str:
        """Создает директорию."""
        return self._fs_tools.create_dir(path)  # type: ignore[no-any-return]

    def move_file(self, src: str, dst: str) -> str:
        """Перемещает или переименовывает файл."""
        return self._fs_tools.move_file(src, dst)  # type: ignore[no-any-return]

    def delete_file(self, path: str) -> str:
        """Удаляет файл или директорию."""
        return self._fs_tools.delete_file(path)  # type: ignore[no-any-return]

    def copy_file(self, src: str, dst: str) -> str:
        """Копирует файл или директорию."""
        return self._fs_tools.copy_file(src, dst)  # type: ignore[no-any-return]

    # SearchTools
    def search_in_files(
        self, query: str, path: str = ".", file_glob: str = "*.py"
    ) -> str:
        """Ищет строку или regex в файлах проекта."""
        return self._search_tools.search_in_files(query, path, file_glob)  # type: ignore[no-any-return]

    def find_files(self, pattern: str, directory: str = ".") -> str:
        """Находит файлы по шаблону имени."""
        return self._search_tools.find_files(pattern, directory)  # type: ignore[no-any-return]

    def grep_in_file(self, path: str, pattern: str, context_lines: int = 2) -> str:
        """Поиск по содержимому одного файла."""
        return self._search_tools.grep_in_file(path, pattern, context_lines)  # type: ignore[no-any-return]

    # InfoTools
    def get_file_size(self, path: str) -> str:
        """Возвращает размер файла в байтах."""
        return self._info_tools.get_file_size(path)  # type: ignore[no-any-return]

    def get_file_info(self, path: str) -> str:
        """Возвращает информацию о файле."""
        return self._info_tools.get_file_info(path)  # type: ignore[no-any-return]

    def count_lines(self, path: str) -> str:
        """Подсчитывает количество строк в файле."""
        return self._info_tools.count_lines(path)  # type: ignore[no-any-return]

    def tail_file(self, path: str, num_lines: int = 20) -> str:
        """Просмотр последних N строк файла."""
        return self._info_tools.tail_file(path, num_lines)  # type: ignore[no-any-return]

    def head_file(self, path: str, num_lines: int = 20) -> str:
        """Просмотр первых N строк файла."""
        return self._info_tools.head_file(path, num_lines)  # type: ignore[no-any-return]

    def get_project_stats(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Возвращает общую статистику проекта."""
        return self._info_tools.get_project_stats(path, file_glob)  # type: ignore[no-any-return]

    # CommandTools
    def run_command(self, command: str) -> str:
        """Запускает команду в терминале."""
        return self._command_tools.run_command(command)  # type: ignore[no-any-return]

    def run_tests(
        self, path: str = ".", verbose: bool = True, timeout: int = 120
    ) -> str:
        """Запускает тесты в указанном пути."""
        return self._command_tools.run_tests(path, verbose, timeout)  # type: ignore[no-any-return]

    def format_code(
        self, path: str = ".", tool: str = "black", check_only: bool = False
    ) -> str:
        """Форматирует код с помощью утилит."""
        return self._command_tools.format_code(path, tool, check_only)  # type: ignore[no-any-return]

    def install_package(
        self, package: str, upgrade: bool = False, user_install: bool = False
    ) -> str:
        """Устанавливает Python-пакет."""
        return self._command_tools.install_package(package, upgrade, user_install)  # type: ignore[no-any-return]

    # BadCaseTools
    def report_bad_case(
        self,
        user_input: str,
        ai_response: str,
        error_type: str,
        error_details: str = "",
    ) -> str:
        """Регистрирует проблемный случай."""
        return self._bad_case_tools.report_bad_case(  # type: ignore[no-any-return]
            user_input, ai_response, error_type, error_details
        )

    def list_bad_cases(self, limit: int = 10, unresolved_only: bool = False) -> str:
        """Показывает список проблемных случаев."""
        return self._bad_case_tools.list_bad_cases(limit, unresolved_only)  # type: ignore[no-any-return]

    def get_bad_case(self, case_id: str) -> str:
        """Показывает детали конкретного случая."""
        return self._bad_case_tools.get_bad_case(case_id)  # type: ignore[no-any-return]

    def mark_bad_case_resolved(self, case_id: str, notes: str = "") -> str:
        """Отмечает случай как решенный."""
        return self._bad_case_tools.mark_bad_case_resolved(case_id, notes)  # type: ignore[no-any-return]

    def get_bad_cases_stats(self) -> str:
        """Показывает статистику по проблемным случаям."""
        return self._bad_case_tools.get_bad_cases_stats()  # type: ignore[no-any-return]
