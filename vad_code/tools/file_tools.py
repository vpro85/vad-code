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
from ..infrastructure.bad_cases import bad_case_manager
from .permissions import register_tool, ToolRiskLevel


class SimpleLRUCache:
    """Простой LRU-кэш с ограничением по количеству элементов."""

    def __init__(self, max_size: int = 50) -> None:
        self.cache: dict[str, str] = {}
        self.max_size = max_size
        self._order: list[str] = []  # Для отслеживания порядка доступа

    def get(self, key: str) -> tuple[bool, str | None]:
        """Получить значение. Возвращает (found, value)."""
        if key in self.cache:
            self._move_to_end(key)
            return True, self.cache[key]
        return False, None

    def put(self, key: str, value: str) -> None:
        """Добавить значение."""
        if key in self.cache:
            self._move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                self._evict()
        self.cache[key] = value
        if key not in self._order:
            self._order.append(key)

    def pop(self, key: str) -> None:
        """Удалить элемент."""
        self.cache.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def _move_to_end(self, key: str) -> None:
        """Переместить ключ в конец списка (самый свежий)."""
        if key in self._order:
            self._order.remove(key)
            self._order.append(key)

    def _evict(self) -> None:
        """Удалить самый старый элемент."""
        if self._order:
            oldest_key = self._order.pop(0)
            self.cache.pop(oldest_key, None)


TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

# Константы для инструментов
_IGNORE_PATTERNS = {".git", "__pycache__", ".venv", ".mypy_cache", ".idea", "node_modules"}
_MAX_SEARCH_RESULTS = 50
_ALLOWED_COMMANDS = {"pytest", "pylint", "flake8", "mypy"}





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


class FindFilesSchema(BaseModel):
    """Схема для поиска файлов по шаблону."""
    pattern: str = Field(..., description="Шаблон имени файла, например '*.py' или 'test_*.py'")
    directory: str = Field(".", description="Директория для поиска")


class TailFileSchema(BaseModel):
    """Схема для просмотра последних строк файла."""
    path: str = Field(..., description="Путь к файлу")
    num_lines: int = Field(20, description="Количество строк с конца файла", ge=1, le=500)


class HeadFileSchema(BaseModel):
    """Схема для просмотра первых строк файла."""
    path: str = Field(..., description="Путь к файлу")
    num_lines: int = Field(20, description="Количество строк с начала файла", ge=1, le=500)


class GetFileInfoSchema(BaseModel):
    """Схема для получения информации о файле."""
    path: str = Field(..., description="Путь к файлу или директории")


class CountLinesSchema(BaseModel):
    """Схема для подсчета строк в файле или директории."""
    path: str = Field(..., description="Путь к файлу или директории")


class GrepInFileSchema(BaseModel):
    """Схема для поиска по содержимому одного файла."""
    path: str = Field(..., description="Путь к файлу")
    pattern: str = Field(..., description="Строка или regex для поиска")
    context_lines: int = Field(
        2,
        description="Количество строк контекста вокруг совпадения",
        ge=0,
        le=20,
    )


class GetProjectStatsSchema(BaseModel):
    """Схема для получения статистики проекта."""
    path: str = Field(".", description="Корневая директория проекта")
    file_glob: str = Field("*.py", description="Маска файлов для анализа, например *.py")


class ReportBadCaseSchema(BaseModel):
    """Схема для ручного добавления проблемного случая."""
    user_input: str = Field(..., description="Входной запрос пользователя")
    ai_response: str = Field(..., description="Ответ AI, который не сработал")
    error_type: str = Field(
        ..., 
        description="Тип ошибки: parse_error, missing_tool_key, invalid_json, no_call_detected, wrong_tool"
    )
    error_details: str = Field("", description="Дополнительные детали ошибки")


class ListBadCasesSchema(BaseModel):
    """Схема для просмотра списка проблемных случаев."""
    limit: int = Field(10, description="Максимальное количество случаев", ge=1, le=50)
    unresolved_only: bool = Field(False, description="Только нерешенные случаи")


class GetBadCaseSchema(BaseModel):
    """Схема для просмотра деталей конкретного случая."""
    case_id: str = Field(..., description="ID случая")


class MarkBadCaseResolvedSchema(BaseModel):
    """Схема для отметки случая как решенного."""
    case_id: str = Field(..., description="ID случая")
    notes: str = Field("", description="Примечания о решении")


class FileTools:
    """Инструменты для работы с файловой системой."""

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

    @register_tool("читает содержимое файла.", schema=ReadFileSchema, risk_level=ToolRiskLevel.READ)
    def read_file(self, path: str) -> str:
        """Читает содержимое файла."""
        try:
            found, cached_content = self._cache.get(path)
            if found:
                return (
                    f"[кэш] Содержимое файла {path}:\n---\n"
                    f"{cached_content}\n---"
                )
            content = self.fs.read_text(path)
            self._cache.put(path, content)
            return f"Содержимое файла {path}:\n---\n{content}\n---"
        except (OSError, ValueError) as e:
            return f"Ошибка при чтении файла: {e}"

    @register_tool("записывает текст в файл (перезаписывает).", schema=WriteFileSchema, risk_level=ToolRiskLevel.WRITE)
    def write_file(self, path: str, content: str) -> str:
        """Записывает текст в файл."""
        try:
            self.fs.write_text(path, content)
            self._cache.put(path, content)  # обновляем кэш
            return f"Файл {path} успешно записан."
        except (OSError, ValueError) as e:
            return f"Ошибка при записи файла {path}: {e}"

    @register_tool(
        "заменяет старый текст на новый в файле.", schema=ReplaceInFileSchema, risk_level=ToolRiskLevel.WRITE
    )
    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        """Заменяет текст в файле."""
        try:
            self.fs.replace_text(path, old_text, new_text)
            self._cache.pop(path)  # инвалидируем кэш после изменения
            return f"Файл {path} успешно обновлен."
        except (OSError, ValueError) as e:
            return f"Ошибка при обновлении файла {path}: {e}"

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
        risk_level=ToolRiskLevel.READ,
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

    @register_tool("создает новую директорию", schema=CreateDirSchema, risk_level=ToolRiskLevel.WRITE)
    def create_dir(self, path: str) -> str:
        """Создает директорию."""
        try:
            self.fs.create_dir(path)
            return f"Директория {path} успешно создана."
        except (OSError, ValueError) as e:
            return f"Ошибка при создании директории {path}: {e}"

    @register_tool(
        "перемещает или переименовывает файл/директорию", schema=MoveFileSchema, risk_level=ToolRiskLevel.WRITE
    )
    def move_file(self, src: str, dst: str) -> str:
        """Перемещает файл или директорию."""
        try:
            self.fs.move_file(src, dst)
            self._cache.pop(src)
            return f"Объект {src} успешно перемещен в {dst}."
        except (OSError, ValueError) as e:
            return f"Ошибка при перемещении {src} -> {dst}: {e}"

    @register_tool("удаляет файл или директорию", schema=DeleteFileSchema, risk_level=ToolRiskLevel.DANGEROUS)
    def delete_file(self, path: str) -> str:
        """Удаляет файл или директорию."""
        try:
            self.fs.delete_file(path)
            self._cache.pop(path)
            return f"Объект {path} успешно удален."
        except (OSError, ValueError) as e:
            return f"Ошибка при удалении {path}: {e}"

    @register_tool(
        "запускает тесты или другие разрешенные команды в терминале",
        schema=RunCommandSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
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
        risk_level=ToolRiskLevel.WRITE,
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
        risk_level=ToolRiskLevel.READ,
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
        "возвращает информацию о файле (размер, даты, права)",
        schema=GetFileInfoSchema,
    )
    def get_file_info(self, path: str) -> str:
        """Возвращает информацию о файле."""
        try:
            import datetime

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
                        f"{j+1}: {l}" for j, l in enumerate(context, start=start)
                    )
                    matches.append(match_block)

            if not matches:
                return f"Совпадений для '{pattern}' в {path} не найдено."

            return "\n---\n".join(matches)
        except re.error as e:
            return f"Ошибка в regex-паттерне: {e}"
        except (OSError, ValueError) as e:
            return f"Ошибка при поиске в файле {path}: {e}"

    @register_tool(
        "общая статистика проекта (количество файлов, строк кода и т.д.)",
        schema=GetProjectStatsSchema,
    )
    def get_project_stats(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Возвращает статистику по файлам проекта."""
        try:
            root = self.fs.safe_path(path)
            files = list(root.rglob(file_glob))
            # Фильтруем служебные папки
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

    @register_tool(
        "регистрирует проблемный случай распознавания команды для последующего анализа",
        schema=ReportBadCaseSchema,
    )
    def report_bad_case(
        self,
        user_input: str,
        ai_response: str,
        error_type: str,
        error_details: str = "",
    ) -> str:
        """Регистрирует проблемный случай."""
        try:
            case_id = bad_case_manager.add_case(
                user_input=user_input,
                ai_response=ai_response,
                error_type=error_type,
                error_details=error_details,
            )
            return f"Проблемный случай зарегистрирован: {case_id}. Теперь вы можете изучить его с помощью get_bad_case."
        except Exception as e:
            return f"Ошибка при регистрации случая: {e}"

    @register_tool(
        "показывает список проблемных случаев распознавания команд",
        schema=ListBadCasesSchema,
    )
    def list_bad_cases(self, limit: int = 10, unresolved_only: bool = False) -> str:
        """Возвращает список проблемных случаев."""
        try:
            cases = bad_case_manager.list_cases(limit=limit, unresolved_only=unresolved_only)
            if not cases:
                return "Проблемных случаев не найдено."

            lines = [f"Найдено {len(cases)} случаев:"]
            for case in cases:
                status = "✅ Решен" if case.resolved else "❌ Не решен"
                lines.append(
                    f"- [{status}] {case.id} | {case.error_type} | "
                    f"{case.timestamp[:19]} | "
                    f"Запрос: {case.user_input[:50]}..."
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении списка: {e}"

    @register_tool(
        "показывает детали конкретного проблемного случая",
        schema=GetBadCaseSchema,
    )
    def get_bad_case(self, case_id: str) -> str:
        """Возвращает детали случая."""
        try:
            case = bad_case_manager.get_case(case_id)
            if not case:
                return f"Случай {case_id} не найден."

            status = "✅ Решен" if case.resolved else "❌ Не решен"
            lines = [
                f"ID: {case.id}",
                f"Статус: {status}",
                f"Время: {case.timestamp}",
                f"Тип ошибки: {case.error_type}",
                f"Детали: {case.error_details}",
                "---",
                f"Запрос пользователя:\n{case.user_input}",
                "---",
                f"Ответ AI:\n{case.ai_response}",
            ]
            if case.resolved and case.resolution_notes:
                lines.extend(["---", f"Решение:\n{case.resolution_notes}"])
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении деталей: {e}"

    @register_tool(
        "отмечает проблемный случай как решенный",
        schema=MarkBadCaseResolvedSchema,
    )
    def mark_bad_case_resolved(self, case_id: str, notes: str = "") -> str:
        """Отмечает случай как решенный."""
        try:
            success = bad_case_manager.mark_resolved(case_id, notes)
            if success:
                return f"Случай {case_id} отмечен как решенный."
            return f"Случай {case_id} не найден."
        except Exception as e:
            return f"Ошибка при отметке: {e}"

    @register_tool(
        "показывает статистику по проблемным случаям",
    )
    def get_bad_cases_stats(self) -> str:
        """Возвращает статистику по проблемным случаям."""
        try:
            stats = bad_case_manager.get_stats()
            lines = [
                "Статистика проблемных случаев:",
                f"- Всего: {stats['total']}",
                f"- Решено: {stats['resolved']}",
                f"- Не решено: {stats['unresolved']}",
                "- По типам:",
            ]
            for error_type, count in stats.get("by_type", {}).items():
                lines.append(f"  - {error_type}: {count}")
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении статистики: {e}"
