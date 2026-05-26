"""
Модуль инструментов для работы с файловой системой.
"""
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, Field

from ..infrastructure.file_system import FileSystemService

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

# Константы для инструментов
_IGNORE_PATTERNS = {".git", "__pycache__", ".venv", ".mypy_cache", ".idea", "node_modules"}
_MAX_SEARCH_RESULTS = 50
_ALLOWED_COMMANDS = {"pytest", "pylint", "flake8", "mypy"}


def register_tool(
    description: str,
    schema: Optional[Type[BaseModel]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор для автоматической регистрации методов как инструментов AI."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        TOOL_REGISTRY[func.__name__] = {
            "description": description,
            "schema": schema,
            "func_name": func.__name__,
        }
        return func

    return decorator


# --- Схемы валидации аргументов ---

class ListFilesSchema(BaseModel):
    """Схема для списка файлов."""
    path: str = Field(".", description="Путь к директории")


class ListTreeSchema(BaseModel):
    """Схема для дерева файлов."""
    path: str = Field(".", description="Корневая директория")
    depth: int = Field(2, description="Глубина обхода (1-5)", ge=1, le=5)


class ReadFileSchema(BaseModel):
    """Схема для чтения файла."""
    path: str = Field(..., description="Путь к файлу")


class WriteFileSchema(BaseModel):
    """Схема для записи файла."""
    path: str = Field(..., description="Путь к файлу")
    content: str = Field(..., description="Текст для записи в файл")


class ReplaceInFileSchema(BaseModel):
    """Схема для замены текста в файле."""
    path: str = Field(..., description="Путь к файлу")
    old_text: str = Field(..., description="Текст, который нужно заменить")
    new_text: str = Field(..., description="Новый текст")


class SearchInFilesSchema(BaseModel):
    """Схема для поиска в файлах."""
    query: str = Field(..., description="Строка или regex для поиска")
    path: str = Field(".", description="Директория для поиска")
    file_glob: str = Field("*.py", description="Маска файлов, например *.py")


class ReadFileLinesSchema(BaseModel):
    """Схема для чтения строк файла."""
    path: str = Field(..., description="Путь к файлу")
    start_line: int = Field(1, description="Номер начальной строки (начиная с 1)")
    end_line: int = Field(100, description="Номер конечной строки")


class CreateDirSchema(BaseModel):
    """Схема для создания директории."""
    path: str = Field(..., description="Путь к директории, которую нужно создать")


class MoveFileSchema(BaseModel):
    """Схема для перемещения файла."""
    src: str = Field(..., description="Путь к исходному файлу или папке")
    dst: str = Field(..., description="Путь назначения")


class DeleteFileSchema(BaseModel):
    """Схема для удаления файла."""
    path: str = Field(..., description="Путь к файлу или папке для удаления")


class RunCommandSchema(BaseModel):
    """Схема для запуска команды."""
    command: str = Field(
        ..., description="Команда для запуска (например, 'pytest tests/test_file_system.py')"
    )


class CopyFileSchema(BaseModel):
    """Схема для копирования файла."""
    src: str = Field(..., description="Путь к исходному файлу или папке")
    dst: str = Field(..., description="Путь назначения")


class GetFileSizeSchema(BaseModel):
    """Схема для получения размера файла."""
    path: str = Field(..., description="Путь к файлу или директории")


class FileTools:
    """Инструменты для работы с файловой системой."""

    def __init__(self) -> None:
        self.fs = FileSystemService()
        self._cache: dict[str, str] = {}

    @register_tool(
        "возвращает плоский список файлов в папке (без рекурсии).",
        schema=ListFilesSchema,
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

    @register_tool("читает содержимое файла.", schema=ReadFileSchema)
    def read_file(self, path: str) -> str:
        """Читает содержимое файла."""
        try:
            if path in self._cache:
                return (
                    f"[кэш] Содержимое файла {path}:\n---\n"
                    f"{self._cache[path]}\n---"
                )
            content = self.fs.read_text(path)
            self._cache[path] = content
            return f"Содержимое файла {path}:\n---\n{content}\n---"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении файла: {e}"

    @register_tool("записывает текст в файл (перезаписывает).", schema=WriteFileSchema)
    def write_file(self, path: str, content: str) -> str:
        """Записывает текст в файл."""
        try:
            self.fs.write_text(path, content)
            self._cache[path] = content  # обновляем кэш
            return f"Файл {path} успешно записан."
        except (OSError, ValueError) as e:
            return f"Ошибка при записи файла {path}: {e}"

    @register_tool(
        "заменяет старый текст на новый в файле.", schema=ReplaceInFileSchema
    )
    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        """Заменяет текст в файле."""
        try:
            self.fs.replace_text(path, old_text, new_text)
            self._cache.pop(path, None)  # инвалидируем кэш после изменения
            return f"Файл {path} успешно обновлен."
        except (OSError, ValueError) as e:
            return f"Ошибка при обновлении файла {path}: {e}"

    @register_tool(
        "ищет строку или regex в файлах проекта — используй вместо "
        "последовательных read_file.",
        schema=SearchInFilesSchema,
    )
    def search_in_files(
        self, query: str, path: str = ".", file_glob: str = "*.py"
    ) -> str:
        """Ищет строку или regex в файлах."""
        try:
            root = self.fs.safe_path(path)
            results = []
            compiled = re.compile(query)

            for filepath in sorted(root.rglob(file_glob)):
                # Не ищем внутри служебных директорий
                if any(part in {".git", "__pycache__", ".venv"} for part in filepath.parts):
                    continue
                try:
                    lines = filepath.read_text(encoding="utf-8").splitlines()
                    for lineno, line in enumerate(lines, 1):
                        if compiled.search(line):
                            rel = filepath.relative_to(root)
                            results.append(f"{rel}:{lineno}: {line.strip()}")
                except (OSError, UnicodeDecodeError):
                    continue  # бинарные файлы и т.п.

            if not results:
                return f"Совпадений для '{query}' не найдено."

            output = "\n".join(results[:_MAX_SEARCH_RESULTS])
            if len(results) > _MAX_SEARCH_RESULTS:
                output += (
                    f"\n[... показано {_MAX_SEARCH_RESULTS} "
                    f"из {len(results)} совпадений ...]"
                )
            return output

        except re.error as e:
            return f"Ошибка в regex-паттерне: {e}"
        except (OSError, ValueError) as e:
            return f"Ошибка при поиске: {e}"

    @register_tool(
        "читает определенный диапазон строк из файла. "
        "Полезно для больших файлов.",
        schema=ReadFileLinesSchema,
    )
    def read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        """Читает диапазон строк из файла."""
        try:
            full_path = self.fs.safe_path(path)
            if not full_path.exists():
                return f"Ошибка: Файл {path} не найден."

            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Корректируем индексы (1-based -> 0-based)
            start_idx = max(0, start_line - 1)
            end_idx = end_line

            selected_lines = lines[start_idx:end_idx]
            content = "".join(selected_lines)

            return f"Строки {start_line}-{min(end_line, len(lines))}:\n\n{content}"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении строк файла: {e}"

    @register_tool("создает новую директорию", schema=CreateDirSchema)
    def create_dir(self, path: str) -> str:
        """Создает директорию."""
        try:
            self.fs.create_dir(path)
            return f"Директория {path} успешно создана."
        except (OSError, ValueError) as e:
            return f"Ошибка при создании директории {path}: {e}"

    @register_tool(
        "перемещает или переименовывает файл/директорию", schema=MoveFileSchema
    )
    def move_file(self, src: str, dst: str) -> str:
        """Перемещает файл или директорию."""
        try:
            self.fs.move_file(src, dst)
            self._cache.pop(src, None)
            return f"Объект {src} успешно перемещен в {dst}."
        except (OSError, ValueError) as e:
            return f"Ошибка при перемещении {src} -> {dst}: {e}"

    @register_tool("удаляет файл или директорию", schema=DeleteFileSchema)
    def delete_file(self, path: str) -> str:
        """Удаляет файл или директорию."""
        try:
            self.fs.delete_file(path)
            self._cache.pop(path, None)
            return f"Объект {path} успешно удален."
        except (OSError, ValueError) as e:
            return f"Ошибка при удалении {path}: {e}"

    @register_tool(
        "запускает тесты или другие разрешенные команды в терминале",
        schema=RunCommandSchema,
    )
    def run_command(self, command: str) -> str:
        """Запускает команду в терминале."""
        try:
            args = shlex.split(command)
            if not args:
                return "Ошибка: пустая команда."

            # Проверка базовой команды
            base_cmd = args[0]
            if base_cmd not in _ALLOWED_COMMANDS:
                return (
                    f"Ошибка: команда '{base_cmd}' запрещена. "
                    f"Разрешены только: {', '.join(_ALLOWED_COMMANDS)}"
                )

            # Запуск команды без shell=True для предотвращения инъекций
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.fs.root,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"

            return output if output.strip() else "Команда выполнена, вывод пуст."

        except subprocess.TimeoutExpired:
            return "Ошибка: время выполнения команды истекло (таймаут 60с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при выполнении команды: {e}"

    @register_tool(
        "копирует файл или директорию",
        schema=CopyFileSchema,
    )
    def copy_file(self, src: str, dst: str) -> str:
        """Копирует файл или директорию."""
        try:
            self.fs.copy_file(src, dst)
            return f"Объект {src} успешно скопирован в {dst}."
        except (OSError, ValueError) as e:
            return f"Ошибка при копировании {src} -> {dst}: {e}"

    @register_tool(
        "возвращает размер файла в байтах или общий размер директории",
        schema=GetFileSizeSchema,
    )
    def get_file_size(self, path: str) -> str:
        """Возвращает размер файла или директории."""
        try:
            size = self.fs.get_file_size(path)
            # Форматируем размер для удобства чтения
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
