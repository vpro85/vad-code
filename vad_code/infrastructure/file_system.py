"""
Сервис для работы с файловой системой.
"""
import shutil
from pathlib import Path

from ..config import settings


class FileSystemService:
    """Сервис для безопасной работы с файловой системой."""

    def __init__(self) -> None:
        self.root = Path(settings.project_root).resolve()

    def safe_path(self, path: str) -> Path:
        """Проверяет, что путь находится внутри разрешенной директории."""
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise PermissionError(f"Доступ запрещен: {target} вне рабочей директории.")
        return target

    def list_dir(self, directory: str) -> list[str]:
        """Возвращает список имен файлов в директоре."""
        path = self.safe_path(directory)
        return [f.name for f in path.iterdir()]

    def read_text(self, filepath: str) -> str:
        """Читает содержимое файла."""
        path = self.safe_path(filepath)
        return path.read_text(encoding="utf-8")

    def write_text(self, filepath: str, content: str) -> None:
        """Записывает текст в файл."""
        path = self.safe_path(filepath)
        path.write_text(content, encoding="utf-8")

    def replace_text(self, filepath: str, old_text: str, new_text: str) -> None:
        """Заменяет текст в файле."""
        path = self.safe_path(filepath)
        content = path.read_text(encoding="utf-8")
        if old_text not in content:
            raise ValueError("Текст для замены не найден.")
        new_content = content.replace(old_text, new_text)
        path.write_text(new_content, encoding="utf-8")

    def create_dir(self, directory: str) -> None:
        """Создает директорию."""
        path = self.safe_path(directory)
        path.mkdir(parents=True, exist_ok=True)

    def move_file(self, src: str, dst: str) -> None:
        """Перемещает файл или директорию."""
        src_path = self.safe_path(src)
        dst_path = self.safe_path(dst)
        src_path.rename(dst_path)

    def delete_file(self, filepath: str) -> None:
        """Удаляет файл или директорию."""
        path = self.safe_path(filepath)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def copy_file(self, src: str, dst: str) -> None:
        """Копирует файл или директорию."""
        src_path = self.safe_path(src)
        dst_path = self.safe_path(dst)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)

    def get_file_size(self, filepath: str) -> int:
        """Возвращает размер файла в байтах."""
        path = self.safe_path(filepath)
        if path.is_dir():
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total
        return path.stat().st_size

    def find_files(self, pattern: str, directory: str = ".") -> list[str]:
        """Находит файлы по шаблону имени."""
        path = self.safe_path(directory)
        return [str(p.relative_to(path)) for p in path.rglob(pattern)]

    def tail_file(self, filepath: str, num_lines: int = 20) -> str:
        """Возвращает последние N строк файла."""
        path = self.safe_path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-num_lines:])

    def head_file(self, filepath: str, num_lines: int = 20) -> str:
        """Возвращает первые N строк файла."""
        path = self.safe_path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[:num_lines])

    def get_file_info(self, filepath: str) -> dict:
        """Возвращает информацию о файле."""
        path = self.safe_path(filepath)
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
        }

    def count_lines(self, filepath: str) -> int:
        """Подсчитывает количество строк в файле или директории."""
        path = self.safe_path(filepath)
        if path.is_dir():
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        with open(f, "r", encoding="utf-8") as file:
                            total += sum(1 for _ in file)
                    except (UnicodeDecodeError, PermissionError):
                        pass
            return total
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
