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
