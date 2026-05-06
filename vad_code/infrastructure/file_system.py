from pathlib import Path

from ..config import settings


class FileSystemService:
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
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()
