from ..infrastructure.file_system import FileSystemService

TOOL_REGISTRY = {}


def register_tool(description: str):
    """Декоратор для автоматической регистрации методов как инструментов AI"""

    def decorator(func):
        # Сохраняем описание и имя функции в глобальный реестр
        TOOL_REGISTRY[func.__name__] = {
            "description": description,
            "func_name": func.__name__
        }
        return func

    return decorator


class FileTools:
    def __init__(self) -> None:
        self.fs = FileSystemService()

    @register_tool("возвращает список файлов в папке.")
    def list_files(self, directory: str = ".") -> str:
        try:
            files = self.fs.list_dir(directory)
            return f"Файлы в {directory}: {', '.join(files)}"
        except Exception as e:
            return f"Ошибка при чтении списка файлов: {str(e)}"

    @register_tool("читает содержимое файла.")
    def read_file(self, filepath: str) -> str:
        try:
            content = self.fs.read_text(filepath)
            return f"Содержимое файла {filepath}:\n---\n{content}\n---"
        except Exception as e:
            return f"Ошибка при чтении файла: {str(e)}"

    @register_tool("записывает текст в файл (перезаписывает).")
    def write_file(self, filepath: str, content: str) -> str:
        try:
            # Обработка экранированных переносов строк (как было в оригинале)
            content = content.replace("\\\\n", "\n")
            self.fs.write_text(filepath, content)
            return f"Файл {filepath} успешно записан."
        except Exception as e:
            return f"Ошибка при записи файла {filepath}: {str(e)}"

    @register_tool("заменяет старый текст на новый в файле.")
    def replace_in_file(self, filepath: str, old_text: str, new_text: str) -> str:
        try:
            new_text = new_text.replace("\\\\n", "\n")
            self.fs.replace_text(filepath, old_text, new_text)
            return f"Файл {filepath} успешно обновлен."
        except Exception as e:
            return f"Ошибка при обновлении файла {filepath}: {str(e)}"
