import re
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from ..infrastructure.file_system import FileSystemService

TOOL_REGISTRY = {}


def register_tool(description: str, schema: Optional[Type[BaseModel]] = None):
    """Декоратор для автоматической регистрации методов как инструментов AI"""

    def decorator(func):
        TOOL_REGISTRY[func.__name__] = {
            "description": description,
            "schema": schema,
            "func_name": func.__name__,
        }
        return func

    return decorator


# --- Схемы валидации аргументов ---

class ListFilesSchema(BaseModel):
    path: str = Field(".", description="Путь к директории")


class ListTreeSchema(BaseModel):
    path: str = Field(".", description="Корневая директория")
    depth: int = Field(2, description="Глубина обхода (1-5)", ge=1, le=5)


class ReadFileSchema(BaseModel):
    path: str = Field(..., description="Путь к файлу")


class WriteFileSchema(BaseModel):
    path: str = Field(..., description="Путь к файлу")
    content: str = Field(..., description="Текст для записи в файл")


class ReplaceInFileSchema(BaseModel):
    path: str = Field(..., description="Путь к файлу")
    old_text: str = Field(..., description="Текст, который нужно заменить")
    new_text: str = Field(..., description="Новый текст")


class SearchInFilesSchema(BaseModel):
    pattern: str = Field(..., description="Строка или regex для поиска")
    path: str = Field(".", description="Директория для поиска")
    file_glob: str = Field("*.py", description="Маска файлов, например *.py")


class FileTools:
    def __init__(self) -> None:
        self.fs = FileSystemService()
        self._cache: dict[str, str] = {}

    @register_tool("возвращает плоский список файлов в папке (без рекурсии).", schema=ListFilesSchema)
    def list_files(self, path: str = ".") -> str:
        try:
            files = self.fs.list_dir(path)
            return f"Файлы в {path}: {', '.join(files)}"
        except Exception as e:
            return f"Ошибка при чтении списка файлов: {e}"

    @register_tool(
        "возвращает дерево файлов рекурсивно — предпочтительный способ изучить структуру проекта.",
        schema=ListTreeSchema,
    )
    def list_tree(self, path: str = ".", depth: int = 2) -> str:
        try:
            root = self.fs.safe_path(path)

            IGNORE = {".git", "__pycache__", ".venv", ".mypy_cache", ".idea", "node_modules"}

            def _walk(p: Path, current_depth: int, prefix: str = "") -> list[str]:
                if current_depth == 0:
                    return []
                lines = []
                items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
                for i, item in enumerate(items):
                    if item.name in IGNORE:
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
        except Exception as e:
            return f"Ошибка при построении дерева: {e}"

    @register_tool("читает содержимое файла.", schema=ReadFileSchema)
    def read_file(self, path: str) -> str:
        try:
            if path in self._cache:
                return f"[кэш] Содержимое файла {path}:\n---\n{self._cache[path]}\n---"
            content = self.fs.read_text(path)
            self._cache[path] = content
            return f"Содержимое файла {path}:\n---\n{content}\n---"
        except Exception as e:
            return f"Ошибка при чтении файла: {e}"

    @register_tool("записывает текст в файл (перезаписывает).", schema=WriteFileSchema)
    def write_file(self, path: str, content: str) -> str:
        try:
            self.fs.write_text(path, content)
            self._cache[path] = content  # обновляем кэш
            return f"Файл {path} успешно записан."
        except Exception as e:
            return f"Ошибка при записи файла {path}: {e}"

    @register_tool("заменяет старый текст на новый в файле.", schema=ReplaceInFileSchema)
    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        try:
            self.fs.replace_text(path, old_text, new_text)
            self._cache.pop(path, None)  # инвалидируем кэш после изменения
            return f"Файл {path} успешно обновлен."
        except Exception as e:
            return f"Ошибка при обновлении файла {path}: {e}"

    @register_tool(
        "ищет строку или regex в файлах проекта — используй вместо последовательных read_file.",
        schema=SearchInFilesSchema,
    )
    def search_in_files(self, pattern: str, path: str = ".", file_glob: str = "*.py") -> str:
        try:
            root = self.fs.safe_path(path)
            results = []
            compiled = re.compile(pattern)

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
                except Exception:
                    continue  # бинарные файлы и т.п.

            if not results:
                return f"Совпадений для '{pattern}' не найдено."

            MAX_RESULTS = 50
            output = "\n".join(results[:MAX_RESULTS])
            if len(results) > MAX_RESULTS:
                output += f"\n[... показано {MAX_RESULTS} из {len(results)} совпадений ...]"
            return output

        except re.error as e:
            return f"Ошибка в regex-паттерне: {e}"
        except Exception as e:
            return f"Ошибка при поиске: {e}"
