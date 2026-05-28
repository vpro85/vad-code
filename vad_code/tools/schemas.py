"""
Схемы валидации для инструментов.
"""
from pydantic import BaseModel, Field


# --- Файловая система ---

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


class CopyFileSchema(BaseModel):
    """Схема для копирования файла."""
    src: str = Field(..., description="Путь к исходному файлу или папке")
    dst: str = Field(..., description="Путь назначения")


# --- Поиск ---

class SearchInFilesSchema(BaseModel):
    """Схема для поиска в файлах."""
    query: str = Field(..., description="Строка или regex для поиска")
    path: str = Field(".", description="Директория для поиска")
    file_glob: str = Field("*.py", description="Маска файлов, например *.py")


class FindFilesSchema(BaseModel):
    """Схема для поиска файлов по шаблону."""
    pattern: str = Field(..., description="Шаблон имени файла, например '*.py' или 'test_*.py'")
    directory: str = Field(".", description="Директория для поиска")


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


# --- Информация о файлах ---

class GetFileSizeSchema(BaseModel):
    """Схема для получения размера файла."""
    path: str = Field(..., description="Путь к файлу или директории")


class GetFileInfoSchema(BaseModel):
    """Схема для получения информации о файле."""
    path: str = Field(..., description="Путь к файлу или директории")


class CountLinesSchema(BaseModel):
    """Схема для подсчета строк в файле или директории."""
    path: str = Field(..., description="Путь к файлу или директории")


class TailFileSchema(BaseModel):
    """Схема для просмотра последних строк файла."""
    path: str = Field(..., description="Путь к файлу")
    num_lines: int = Field(20, description="Количество строк с конца файла", ge=1, le=500)


class HeadFileSchema(BaseModel):
    """Схема для просмотра первых строк файла."""
    path: str = Field(..., description="Путь к файлу")
    num_lines: int = Field(20, description="Количество строк с начала файла", ge=1, le=500)


class GetProjectStatsSchema(BaseModel):
    """Схема для получения статистики проекта."""
    path: str = Field(".", description="Корневая директория проекта")
    file_glob: str = Field("*.py", description="Маска файлов для анализа, например *.py")


# --- Команды ---

class RunCommandSchema(BaseModel):
    """Схема для запуска команды."""
    command: str = Field(
        ..., description="Команда для запуска (например, 'pytest tests/test_file_system.py')"
    )


class RunTestsSchema(BaseModel):
    """Схема для запуска тестов."""
    path: str = Field(".", description="Путь к файлу или директории с тестами")
    verbose: bool = Field(True, description="Подробный вывод")
    timeout: int = Field(120, description="Таймаут в секундах", ge=10, le=600)


class FormatCodeSchema(BaseModel):
    """Схема для форматирования кода."""
    path: str = Field(".", description="Путь к файлу или директории")
    tool: str = Field("black", description="Инструмент форматирования: black, autopep8, isort")
    check_only: bool = Field(False, description="Только проверка без изменения файлов")


class InstallPackageSchema(BaseModel):
    """Схема для установки Python-пакетов."""
    package: str = Field(..., description="Имя пакета для установки (например, 'requests' или 'numpy>=1.21')")
    upgrade: bool = Field(False, description="Обновить пакет до последней версии")
    user_install: bool = Field(False, description="Установить в пользовательскую директорию")


class UninstallPackageSchema(BaseModel):
    """Схема для удаления Python-пакетов."""
    package: str = Field(..., description="Имя пакета для удаления (например, 'requests')")


class ListPackagesSchema(BaseModel):
    """Схема для списка установленных пакетов."""
    filter_pattern: str = Field("", description="Фильтр по имени пакета")
    show_upgradable: bool = Field(False, description="Показать только пакеты, доступные для обновления")


class UpdatePackageSchema(BaseModel):
    """Схема для обновления Python-пакетов."""
    package: str = Field("", description="Имя пакета. Пустая строка = обновить все")
    user_install: bool = Field(False, description="Обновить в пользовательской директории")


class RunLinterSchema(BaseModel):
    """Схема для запуска линтеров."""
    tool: str = Field("pylint", description="Инструмент: pylint, flake8, mypy")
    path: str = Field(".", description="Путь к файлу или директории")
    args: str = Field("", description="Дополнительные аргументы")


class SearchAndReplaceSchema(BaseModel):
    """Схема для массовой замены."""
    search_pattern: str = Field(..., description="Шаблон для поиска (regex)")
    replace_with: str = Field(..., description="Текст замены")
    path: str = Field(".", description="Директория для поиска")
    file_glob: str = Field("*.py", description="Маска файлов")
    dry_run: bool = Field(True, description="Только показать что будет заменено")


class FindDuplicatesSchema(BaseModel):
    """Схема для поиска дублирующегося кода."""
    path: str = Field(".", description="Директория для анализа")
    min_lines: int = Field(5, description="Минимальное кол-во строк", ge=2, le=50)
    file_glob: str = Field("*.py", description="Маска файлов")


class AnalyzeComplexitySchema(BaseModel):
    """Схема для анализа сложности кода."""
    path: str = Field(".", description="Путь к файлу или директории")
    threshold: int = Field(10, description="Порог сложности", ge=1, le=50)


class FindCodeSmellsSchema(BaseModel):
    """Схема для поиска запахов кода."""
    path: str = Field(".", description="Путь к файлу или директории")
    file_glob: str = Field("*.py", description="Маска файлов")


class GenerateDocstringSchema(BaseModel):
    """Схема для генерации docstring."""
    path: str = Field(..., description="Путь к файлу")
    function_name: str = Field("", description="Имя функции. Пусто = для всех")
    style: str = Field("google", description="Стиль: google, numpy, sphinx")


class AnalyzeDependenciesSchema(BaseModel):
    """Схема для анализа зависимостей."""
    path: str = Field(".", description="Путь к файлу или директории")
    file_glob: str = Field("*.py", description="Маска файлов")


class FindUnusedImportsSchema(BaseModel):
    """Схема для поиска неиспользуемых импортов."""
    path: str = Field(".", description="Путь к файлу или директории")
    file_glob: str = Field("*.py", description="Маска файлов")


class ListProcessesSchema(BaseModel):
    """Схема для списка процессов."""
    filter_pattern: str = Field("", description="Фильтр по имени процесса")


class KillProcessSchema(BaseModel):
    """Схема для завершения процесса."""
    pid: int = Field(..., description="PID процесса")
    force: bool = Field(False, description="Принудительное завершение")


class RunBackgroundTaskSchema(BaseModel):
    """Схема для запуска фоновой задачи."""
    command: str = Field(..., description="Команда для выполнения")
    timeout: int = Field(300, description="Таймаут в секундах", ge=10, le=3600)


# --- Проблемные случаи ---

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
