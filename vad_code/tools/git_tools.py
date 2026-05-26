"""
Модуль инструментов для работы с Git.
"""
import subprocess
from typing import Optional

from pydantic import BaseModel, Field

from .file_tools import register_tool
from ..infrastructure.file_system import FileSystemService


# --- Схемы валидации аргументов ---

class GitStatusSchema(BaseModel):
    """Схема для git status."""
    pass


class GitDiffSchema(BaseModel):
    """Схема для git diff."""
    path: Optional[str] = Field(None,
                                description="Путь к конкретному файлу для просмотра разницы. Если None, показывает все изменения.")


class GitAddSchema(BaseModel):
    """Схема для git add."""
    path: str = Field(..., description="Путь к файлу или '.' для всех файлов")


class GitCommitSchema(BaseModel):
    """Схема для git commit."""
    message: str = Field(..., description="Сообщение коммита")


class GitLogSchema(BaseModel):
    """Схема для git log."""
    limit: int = Field(10, description="Количество последних коммитов для отображения")


class GitBranchSchema(BaseModel):
    """Схема для git branch."""
    name: Optional[str] = Field(None, description="Имя ветки. Если None, показывает список веток.")


class GitCheckoutSchema(BaseModel):
    """Схема для git checkout."""
    target: str = Field(..., description="Ветка или путь к файлу для восстановления")


class GitShowSchema(BaseModel):
    """Схема для git show."""
    commit_hash: str = Field(..., description="Хэш коммита для просмотра")


class GitStashSchema(BaseModel):
    """Схема для git stash."""
    action: str = Field(..., description="Действие: 'push', 'pop', 'list' или 'apply'")


class GitMergeSchema(BaseModel):
    """Схема для git merge."""
    branch: str = Field(..., description="Имя ветки для слияния")


class GitBlameSchema(BaseModel):
    """Схема для git blame."""
    path: str = Field(..., description="Путь к файлу для просмотра истории изменений по строкам")


class GitLogFileSchema(BaseModel):
    """Схема для git log конкретного файла."""
    path: str = Field(..., description="Путь к файлу")
    limit: int = Field(10, description="Количество последних коммитов для отображения")


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

    @register_tool(
        "показывает историю коммитов.",
        schema=GitLogSchema,
    )
    def git_log(self, limit: int = 10) -> str:
        """Выполняет git log."""
        return self._run_git(["log", f"-n {limit}", "--oneline"])

    @register_tool(
        "показывает список веток или создает новую.",
        schema=GitBranchSchema,
    )
    def git_branch(self, name: Optional[str] = None) -> str:
        """Выполняет git branch."""
        args = ["branch"]
        if name:
            args.append(name)
        return self._run_git(args)

    @register_tool(
        "переключает ветку или восстанавливает файл из индекса.",
        schema=GitCheckoutSchema,
    )
    def git_checkout(self, target: str) -> str:
        """Выполняет git checkout."""
        return self._run_git(["checkout", target])

    @register_tool(
        "показывает детали конкретного коммита.",
        schema=GitShowSchema,
    )
    def git_show(self, commit_hash: str) -> str:
        """Выполняет git show."""
        return self._run_git(["show", commit_hash])

    @register_tool(
        "управляет временным хранилищем изменений (stash).",
        schema=GitStashSchema,
    )
    def git_stash(self, action: str) -> str:
        """Выполняет git stash."""
        return self._run_git(["stash", action])

    @register_tool(
        "сливает указанную ветку в текущую.",
        schema=GitMergeSchema,
    )
    def git_merge(self, branch: str) -> str:
        """Выполняет git merge."""
        return self._run_git(["merge", branch])

    @register_tool(
        "показывает историю изменений по строкам файла (git blame).",
        schema=GitBlameSchema,
    )
    def git_blame(self, path: str) -> str:
        """Выполняет git blame."""
        return self._run_git(["blame", "--porcelain", path])

    @register_tool(
        "показывает историю изменений конкретного файла.",
        schema=GitLogFileSchema,
    )
    def git_log_file(self, path: str, limit: int = 10) -> str:
        """Выполняет git log для конкретного файла."""
        return self._run_git(["log", f"-n {limit}", "--oneline", "--", path])
