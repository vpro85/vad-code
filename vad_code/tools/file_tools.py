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
        return self._fs_tools.list_files(path)  # type: ignore[no-any-return]

    def list_tree(self, path: str = ".", depth: int = 2) -> str:
        return self._fs_tools.list_tree(path, depth)  # type: ignore[no-any-return]

    def read_file(self, path: str) -> str:
        return self._fs_tools.read_file(path)  # type: ignore[no-any-return]

    def write_file(self, path: str, content: str) -> str:
        return self._fs_tools.write_file(path, content)  # type: ignore[no-any-return]

    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        return self._fs_tools.replace_in_file(path, old_text, new_text)  # type: ignore[no-any-return]

    def read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        return self._fs_tools.read_file_lines(path, start_line, end_line)  # type: ignore[no-any-return]

    def create_dir(self, path: str) -> str:
        return self._fs_tools.create_dir(path)  # type: ignore[no-any-return]

    def move_file(self, src: str, dst: str) -> str:
        return self._fs_tools.move_file(src, dst)  # type: ignore[no-any-return]

    def delete_file(self, path: str) -> str:
        return self._fs_tools.delete_file(path)  # type: ignore[no-any-return]

    def copy_file(self, src: str, dst: str) -> str:
        return self._fs_tools.copy_file(src, dst)  # type: ignore[no-any-return]

    # SearchTools
    def search_in_files(
        self, query: str, path: str = ".", file_glob: str = "*.py"
    ) -> str:
        return self._search_tools.search_in_files(query, path, file_glob)  # type: ignore[no-any-return]

    def find_files(self, pattern: str, directory: str = ".") -> str:
        return self._search_tools.find_files(pattern, directory)  # type: ignore[no-any-return]

    def grep_in_file(self, path: str, pattern: str, context_lines: int = 2) -> str:
        return self._search_tools.grep_in_file(path, pattern, context_lines)  # type: ignore[no-any-return]

    # InfoTools
    def get_file_size(self, path: str) -> str:
        return self._info_tools.get_file_size(path)  # type: ignore[no-any-return]

    def get_file_info(self, path: str) -> str:
        return self._info_tools.get_file_info(path)  # type: ignore[no-any-return]

    def count_lines(self, path: str) -> str:
        return self._info_tools.count_lines(path)  # type: ignore[no-any-return]

    def tail_file(self, path: str, num_lines: int = 20) -> str:
        return self._info_tools.tail_file(path, num_lines)  # type: ignore[no-any-return]

    def head_file(self, path: str, num_lines: int = 20) -> str:
        return self._info_tools.head_file(path, num_lines)  # type: ignore[no-any-return]

    def get_project_stats(self, path: str = ".", file_glob: str = "*.py") -> str:
        return self._info_tools.get_project_stats(path, file_glob)  # type: ignore[no-any-return]

    # CommandTools
    def run_command(self, command: str) -> str:
        return self._command_tools.run_command(command)  # type: ignore[no-any-return]

    def run_tests(
        self, path: str = ".", verbose: bool = True, timeout: int = 120
    ) -> str:
        return self._command_tools.run_tests(path, verbose, timeout)  # type: ignore[no-any-return]

    def format_code(
        self, path: str = ".", tool: str = "black", check_only: bool = False
    ) -> str:
        return self._command_tools.format_code(path, tool, check_only)  # type: ignore[no-any-return]

    def install_package(
        self, package: str, upgrade: bool = False, user_install: bool = False
    ) -> str:
        return self._command_tools.install_package(package, upgrade, user_install)  # type: ignore[no-any-return]

    # BadCaseTools
    def report_bad_case(
        self,
        user_input: str,
        ai_response: str,
        error_type: str,
        error_details: str = "",
    ) -> str:
        return self._bad_case_tools.report_bad_case(  # type: ignore[no-any-return]
            user_input, ai_response, error_type, error_details
        )

    def list_bad_cases(self, limit: int = 10, unresolved_only: bool = False) -> str:
        return self._bad_case_tools.list_bad_cases(limit, unresolved_only)  # type: ignore[no-any-return]

    def get_bad_case(self, case_id: str) -> str:
        return self._bad_case_tools.get_bad_case(case_id)  # type: ignore[no-any-return]

    def mark_bad_case_resolved(self, case_id: str, notes: str = "") -> str:
        return self._bad_case_tools.mark_bad_case_resolved(case_id, notes)  # type: ignore[no-any-return]

    def get_bad_cases_stats(self) -> str:
        return self._bad_case_tools.get_bad_cases_stats()  # type: ignore[no-any-return]
