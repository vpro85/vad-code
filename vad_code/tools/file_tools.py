from ..infrastructure.file_system import FileSystemService


class FileTools:
    def __init__(self) -> None:
        self.fs = FileSystemService()

    def list_files(self, directory: str = ".") -> str:
        try:
            files = self.fs.list_dir(directory)
            return f"Файлы в {directory}: {', '.join(files)}"
        except Exception as e:
            return f"Ошибка при чтении списка файлов: {str(e)}"

    def read_file(self, filepath: str) -> str:
        try:
            content = self.fs.read_text(filepath)
            return f"Содержимое файла {filepath}:\n---\n{content}\n---"
        except Exception as e:
            return f"Ошибка при чтении файла: {str(e)}"

    def write_file(self, filepath: str, content: str) -> str:
        try:
            # Обработка экранированных переносов строк (как было в оригинале)
            content = content.replace("\\\\n", "\n")
            self.fs.write_text(filepath, content)
            return f"Файл {filepath} успешно записан."
        except Exception as e:
            return f"Ошибка при записи файла {filepath}: {str(e)}"

    def replace_in_file(self, filepath: str, old_text: str, new_text: str) -> str:
        try:
            new_text = new_text.replace("\\\\n", "\n")
            self.fs.replace_text(filepath, old_text, new_text)
            return f"Файл {filepath} успешно обновлен."
        except Exception as e:
            return f"Ошибка при обновлении файла {filepath}: {str(e)}"
