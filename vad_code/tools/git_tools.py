"""
Модуль инструментов для работы с Git.
"""
import subprocess
from typing import Any, Callable, Optional, Type
from pydantic import BaseModel, Field
from ..infrastructure.file_system import FileSystemService
from .file_tools import register_tool

# --- Схемы валидации аргументов ---

class GitStatusSchema(BaseModel):
    """Схема для git status."""
    pass

class GitDiffSchema(BaseModel):
    """Схема для git diff."""
    path: Optional[str] = Field(None, description="Путь к конкретному файлу для просмотра разницы. Если None, показывает все изменения.")

class GitAddSchema(BaseModel):
    """Схема для git add."""
    path: str = Field(..., description="Путь к файлу или '.' для всех файлов")

class GitCommitSchema(BaseModel):
    """Схема для git commit."""
    message: str = Field(..., description="Сообщение коммита")

class GitTools:
    """Инструменты для работы с Git."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    def _run_git(self, args: list[str]) -> str:
        """Вспомогательный метод для запуска команд git."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.fs.root,
                check=False,
            )
            
            if result.returncode != 0:
                return f"Ошибка Git: {result.stderr}"
            
            return result.stdout if result.stdout.strip() else "Команда выполнена успешно, вывод пуст."
        except Exception as e:
            return f"Критическая ошибка при выполнении git: {e}"

    @register_tool(
        "показывает статус репозитория (какие файлы изменены, удалены или не отслеживаются).",
        schema=GitStatusSchema,
    )
    def git_status(self) -> str:
        """Возвращает вывод git status."""
        return self._run_git(["status", "-s"])

    @register_tool(
        "показывает детальные изменения в коде (diff). Полезно перед коммитом.",
        schema=GitDiffSchema,
    )
    def git_diff(self, path: Optional[str] = None) -> str:
        """Возвращает вывод git diff."""
        args = ["diff"]
        if path:
            args.append(path)
        return self._run_git(args)

    @register_tool(
        "добавляет файлы в индекс (staging area) для последующего коммита.",
        schema=GitAddSchema,
    )
    def git_add(self, path: str) -> str:
        """Выполняет git add."""
        return self._run_git(["add", path])

    @register_tool(
        "создает коммит с указанным сообщением.",
        schema=GitCommitSchema,
    )
    def git_commit(self, message: str) -> str:
        """Выполняет git commit."""
        return self._run_git(["commit", "-m", message])
