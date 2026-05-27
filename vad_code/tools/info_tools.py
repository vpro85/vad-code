"""
Инструменты для получения информации о файлах и проекте.
"""
import datetime

from ..infrastructure.file_system import FileSystemService
from .permissions import register_tool, ToolRiskLevel
from .schemas import (
    GetFileSizeSchema,
    GetFileInfoSchema,
    CountLinesSchema,
    TailFileSchema,
    HeadFileSchema,
    GetProjectStatsSchema,
)


class InfoTools:
    """Инструменты для получения информации о файлах."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    @register_tool(
        "возвращает размер файла в байтах или общий размер директории",
        schema=GetFileSizeSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def get_file_size(self, path: str) -> str:
        """Возвращает размер файла или директории."""
        try:
            size = self.fs.get_file_size(path)
            if size >= 1024 * 1024 * 1024:
                formatted = f"{size / (1024**3):.2f} GB"
            elif size >= 1024 * 1024:
                formatted = f"{size / (1024**2):.2f} MB"
            elif size >= 1024:
                formatted = f"{size / 1024:.2f} KB"
            else:
                formatted = f"{size} bytes"
            return f"Размер {path}: {formatted} ({size} байт)"
        except (OSError, ValueError) as e:
            return f"Ошибка при получении размера {path}: {e}"

    @register_tool(
        "возвращает информацию о файле (размер, даты, права)",
        schema=GetFileInfoSchema,
    )
    def get_file_info(self, path: str) -> str:
        """Возвращает информацию о файле."""
        try:
            info = self.fs.get_file_info(path)
            modified = datetime.datetime.fromtimestamp(
                info["modified"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            accessed = datetime.datetime.fromtimestamp(
                info["accessed"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            return (
                f"Имя: {info['name']}\n"
                f"Путь: {info['path']}\n"
                f"Тип: {'Директория' if info['is_dir'] else 'Файл'}\n"
                f"Размер: {info['size']} байт\n"
                f"Изменен: {modified}\n"
                f"Доступ: {accessed}"
            )
        except (OSError, ValueError) as e:
            return f"Ошибка при получении информации о {path}: {e}"

    @register_tool(
        "подсчитывает количество строк в файле или директории",
        schema=CountLinesSchema,
    )
    def count_lines(self, path: str) -> str:
        """Подсчитывает количество строк."""
        try:
            count = self.fs.count_lines(path)
            return f"Количество строк в {path}: {count}"
        except (OSError, ValueError) as e:
            return f"Ошибка при подсчете строк в {path}: {e}"

    @register_tool(
        "просмотр последних N строк файла (аналог tail)",
        schema=TailFileSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def tail_file(self, path: str, num_lines: int = 20) -> str:
        """Возвращает последние N строк файла."""
        try:
            content = self.fs.tail_file(path, num_lines)
            return f"Последние {num_lines} строк файла {path}:\n---\n{content}---"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении файла {path}: {e}"

    @register_tool(
        "просмотр первых N строк файла (аналог head)",
        schema=HeadFileSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def head_file(self, path: str, num_lines: int = 20) -> str:
        """Возвращает первые N строк файла."""
        try:
            content = self.fs.head_file(path, num_lines)
            return f"Первые {num_lines} строк файла {path}:\n---\n{content}---"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении файла {path}: {e}"

    @register_tool(
        "общая статистика проекта (количество файлов, строк кода и т.д.)",
        schema=GetProjectStatsSchema,
    )
    def get_project_stats(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Возвращает статистику по файлам проекта."""
        try:
            root = self.fs.safe_path(path)
            files = list(root.rglob(file_glob))
            excluded = {".git", "__pycache__", ".venv", "node_modules"}
            files = [
                f for f in files
                if not any(part in excluded for part in f.parts)
            ]

            total_lines = 0
            total_size = 0
            for f in files:
                try:
                    total_lines += len(f.read_text(encoding="utf-8").splitlines())
                    total_size += f.stat().st_size
                except (OSError, UnicodeDecodeError):
                    continue

            return (
                f"Статистика проекта ({path}):\n"
                f"- Файлов ({file_glob}): {len(files)}\n"
                f"- Всего строк: {total_lines}\n"
                f"- Общий размер: {total_size} байт"
            )
        except (OSError, ValueError) as e:
            return f"Ошибка при получении статистики: {e}"
