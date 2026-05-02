from pydantic import BaseModel, Field

class ListFilesSchema(BaseModel):
    directory: str = Field(default=".", description="Путь к директории для листинга файлов")

class ReadFileSchema(BaseModel):
    filepath: str = Field(..., description="Полный путь к файлу для чтения")

class WriteFileSchema(BaseModel):
    filepath: str = Field(..., description="Полный путь к файлу для записи")
    content: str = Field(..., description="Содержимое файла")

class ReplaceInFileSchema(BaseModel):
    filepath: str = Field(..., description="Полный путь к файлу")
    old_text: str = Field(..., description="Текст, который нужно заменить")
    new_text: str = Field(..., description="Новый текст")