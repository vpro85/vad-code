"""
Схемы валидации для инструментов.
"""
from pydantic import BaseModel, Field


class ListFilesSchema(BaseModel):
    """Схема для списка файлов."""
    directory: str = Field(default=".", description="Путь к директории для листинга файлов")


class ReadFileSchema(BaseModel):
    """Схема для чтения файла."""
    filepath: str = Field(..., description="Полный путь к файлу для чтения")


class WriteFileSchema(BaseModel):
    """Схема для записи файла."""
    filepath: str = Field(..., description="Полный путь к файлу для записи")
    content: str = Field(..., description="Содержимое файла")


class ReplaceInFileSchema(BaseModel):
    """Схема для замены текста в файле."""
    filepath: str = Field(..., description="Полный путь к файлу")
    old_text: str = Field(..., description="Текст, который нужно заменить")
    new_text: str = Field(..., description="Новый текст")
