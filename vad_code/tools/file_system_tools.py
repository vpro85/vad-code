"""
Базовые инструменты для работы с файловой системой.
"""

from pathlib import Path

from ..infrastructure.file_system import FileSystemService
from ..infrastructure.cache import SimpleLRUCache
from .permissions import register_tool, ToolRiskLevel
from .schemas import (
    ListFilesSchema,
    ListTreeSchema,
    ReadFileSchema,
    WriteFileSchema,
    ReplaceInFileSchema,
    ReadFileLinesSchema,
    CreateDirSchema,
    MoveFileSchema,
    DeleteFileSchema,
    CopyFileSchema,
)

_IGNORE_PATTERNS = {
    ".git",
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".idea",
    "node_modules",
}


class FileSystemTools:
    """Инструменты для базовых операций с файловой системой."""

    def __init__(self) -> None:
        self.fs = FileSystemService()
        self._cache = SimpleLRUCache(max_size=50)

    @register_tool(
        "возвращает плоский список файлов в папке (без рекурсии).",
        schema=ListFilesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def list_files(self, path: str = ".") -> str:
        """Возвращает список файлов в директории."""
        try:
            files = self.fs.list_dir(path)
            return f"Файлы в {path}: {', '.join(files)}"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении списка файлов: {e}"

    @register_tool(
        "возвращает дерево файлов рекурсивно — предпочтительный способ "
        "изучить структуру проекта.",
        schema=ListTreeSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def list_tree(self, path: str = ".", depth: int = 2) -> str:
        """Возвращает дерево файлов."""
        try:
            root = self.fs.safe_path(path)

            def _walk(p: Path, current_depth: int, prefix: str = "") -> list[str]:
                if current_depth == 0:
                    return []
                lines = []
                items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
                for i, item in enumerate(items):
                    if item.name in _IGNORE_PATTERNS:
                        continue
                    connector = "└── " if i == len(items) - 1 else "├── "
                    icon = "📁" if item.is_dir() else "📄"
                    lines.append(f"{prefix}{connector}{icon} {item.name}")
                    if item.is_dir():
                        extension = "    " if i == len(items) - 1 else "│   "
                        lines.extend(_walk(item, current_depth - 1, prefix + extension))
                return lines

            lines = [f"📁 {path}"] + _walk(root, depth)
            return "\n".join(lines)
        except (OSError, ValueError) as e:
            return f"Ошибка при построении дерева: {e}"

    @register_tool(
        "читает содержимое файла.", schema=ReadFileSchema, risk_level=ToolRiskLevel.READ
    )
    def read_file(self, path: str) -> str:
        """Читает содержимое файла."""
        try:
            found, cached_content = self._cache.get(path)
            if found:
                return f"[кэш] Содержимое файла {path}:\n---\n{cached_content}\n---"
            content = self.fs.read_text(path)
            self._cache.put(path, content)
            return f"Содержимое файла {path}:\n---\n{content}\n---"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении файла: {e}"

    @register_tool(
        "записывает текст в файл (перезаписывает).",
        schema=WriteFileSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def write_file(self, path: str, content: str) -> str:
        """Записывает текст в файл."""
        try:
            self.fs.write_text(path, content)
            self._cache.put(path, content)
            return f"Файл {path} успешно записан."
        except (OSError, ValueError) as e:
            return f"Ошибка при записи файла {path}: {e}"

    @register_tool(
        "заменяет старый текст на новый в файле.",
        schema=ReplaceInFileSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        """Заменяет текст в файле."""
        try:
            self.fs.replace_text(path, old_text, new_text)
            self._cache.pop(path)
            return f"Файл {path} успешно обновлен."
        except (OSError, ValueError) as e:
            return f"Ошибка при обновлении файла {path}: {e}"

    @register_tool(
        "читает определенный диапазон строк из файла. " "Полезно для больших файлов.",
        schema=ReadFileLinesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        """Читает диапазон строк из файла."""
        try:
            full_path = self.fs.safe_path(path)
            if not full_path.exists():
                return f"Ошибка: Файл {path} не найден."

            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            start_idx = max(0, start_line - 1)
            end_idx = end_line

            selected_lines = lines[start_idx:end_idx]
            content = "".join(selected_lines)

            return f"Строки {start_line}-{min(end_line, len(lines))}:\n\n{content}"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении строк файла: {e}"

    @register_tool(
        "создает новую директорию",
        schema=CreateDirSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def create_dir(self, path: str) -> str:
        """Создает директорию."""
        try:
            self.fs.create_dir(path)
            return f"Директория {path} успешно создана."
        except (OSError, ValueError) as e:
            return f"Ошибка при создании директории {path}: {e}"

    @register_tool(
        "перемещает или переименовывает файл/директорию",
        schema=MoveFileSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def move_file(self, src: str, dst: str) -> str:
        """Перемещает файл или директорию."""
        try:
            self.fs.move_file(src, dst)
            self._cache.pop(src)
            return f"Объект {src} успешно перемещен в {dst}."
        except (OSError, ValueError) as e:
            return f"Ошибка при перемещении {src} -> {dst}: {e}"

    @register_tool(
        "удаляет файл или директорию",
        schema=DeleteFileSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def delete_file(self, path: str) -> str:
        """Удаляет файл или директорию."""
        try:
            self.fs.delete_file(path)
            self._cache.pop(path)
            return f"Объект {path} успешно удален."
        except (OSError, ValueError) as e:
            return f"Ошибка при удалении {path}: {e}"

    @register_tool(
        "копирует файл или директорию",
        schema=CopyFileSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def copy_file(self, src: str, dst: str) -> str:
        """Копирует файл или директорию."""
        try:
            self.fs.copy_file(src, dst)
            return f"Объект {src} успешно скопирован в {dst}."
        except (OSError, ValueError) as e:
            return f"Ошибка при копировании {src} -> {dst}: {e}"
