"""
Инструменты для поиска в файлах.
"""

import re

from ..infrastructure.file_system import FileSystemService
from .permissions import register_tool, ToolRiskLevel
from .schemas import SearchInFilesSchema, FindFilesSchema, GrepInFileSchema

_MAX_SEARCH_RESULTS = 50


class SearchTools:
    """Инструменты для поиска в файлах."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    @register_tool(
        "ищет строку или regex в файлах проекта — используй вместо "
        "последовательных read_file.",
        schema=SearchInFilesSchema,
        risk_level=ToolRiskLevel.READ,
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
                if any(
                    part in {".git", "__pycache__", ".venv"} for part in filepath.parts
                ):
                    continue
                try:
                    lines = filepath.read_text(encoding="utf-8").splitlines()
                    for lineno, line in enumerate(lines, 1):
                        if compiled.search(line):
                            rel = filepath.relative_to(root)
                            results.append(f"{rel}:{lineno}: {line.strip()}")
                except OSError, UnicodeDecodeError:
                    continue

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
        "находит файлы по шаблону имени (рекурсивно)",
        schema=FindFilesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def find_files(self, pattern: str, directory: str = ".") -> str:
        """Находит файлы по шаблону."""
        try:
            files = self.fs.find_files(pattern, directory)
            if not files:
                return f"Файлы по шаблону '{pattern}' не найдены."
            return "\n".join(files[:_MAX_SEARCH_RESULTS])
        except (OSError, ValueError) as e:
            return f"Ошибка при поиске файлов: {e}"

    @register_tool(
        "поиск по содержимому одного файла (аналог grep)",
        schema=GrepInFileSchema,
    )
    def grep_in_file(self, path: str, pattern: str, context_lines: int = 2) -> str:
        """Ищет паттерн в файле и возвращает совпадения с контекстом."""
        try:
            full_path = self.fs.safe_path(path)
            if not full_path.exists():
                return f"Ошибка: Файл {path} не найден."

            content = full_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            compiled = re.compile(pattern)

            matches = []
            for i, line in enumerate(lines):
                if compiled.search(line):
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = lines[start:end]
                    match_block = "\n".join(
                        f"{j + 1}: {l}" for j, l in enumerate(context, start=start)
                    )
                    matches.append(match_block)

            if not matches:
                return f"Совпадений для '{pattern}' в {path} не найдено."

            return "\n---\n".join(matches)
        except re.error as e:
            return f"Ошибка в regex-паттерне: {e}"
        except (OSError, ValueError) as e:
            return f"Ошибка при поиске в файле {path}: {e}"
