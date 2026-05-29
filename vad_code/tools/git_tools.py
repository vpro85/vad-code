"""
Модуль инструментов для работы с Git.
"""

import subprocess
from typing import Any

from pydantic import BaseModel, Field

from .permissions import register_tool, ToolRiskLevel
from ..infrastructure.file_system import FileSystemService

# --- Схемы валидации аргументов ---


class GitStatusSchema(BaseModel):
    """Схема для git status."""


class GitDiffSchema(BaseModel):
    """Схема для git diff."""

    path: str | None = Field(
        None,
        description="Путь к конкретному файлу для просмотра разницы. "
        "Если None, показывает все изменения.",
    )


class GitDiffStagedSchema(BaseModel):
    """Схема для git diff --staged."""

    path: str | None = Field(
        None,
        description="Путь к конкретному файлу. "
        "Если None, показывает все staged изменения.",
    )


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

    name: str | None = Field(
        None, description="Имя ветки. Если None, показывает список веток."
    )


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

    path: str = Field(
        ..., description="Путь к файлу для просмотра истории изменений по строкам"
    )


class GitLogFileSchema(BaseModel):
    """Схема для git log конкретного файла."""

    path: str = Field(..., description="Путь к файлу")
    limit: int = Field(10, description="Количество последних коммитов для отображения")


class GitCurrentBranchSchema(BaseModel):
    """Схема для определения текущей ветки."""


class GitSearchCommitsSchema(BaseModel):
    """Схема для поиска коммитов по сообщению."""

    query: str = Field(..., description="Текст для поиска в сообщениях коммитов")
    limit: int = Field(10, description="Количество результатов для отображения")


class GitTools:
    """Инструменты для работы с Git."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    def _run_git(self, args: list[str]) -> str:
        """Вспомогательный метод для запуска команд git."""
        # Валидация аргументов, содержащих пути
        validated_args = []
        for arg in args:
            # Валидируем только аргументы, которые явно выглядят как пути к файлам
            # (содержат '/' или начинаются с '.'), чтобы не ломать имена веток/коммитов
            is_path_like = "/" in arg or arg.startswith(".")

            if is_path_like and not arg.startswith("-"):
                try:
                    safe_path = self.fs.safe_path(arg)
                    validated_args.append(str(safe_path))
                except (ValueError, OSError):
                    return f"Ошибка: Недопустимый путь '{arg}'"
            else:
                validated_args.append(arg)

        try:
            result = subprocess.run(
                ["git"] + validated_args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.fs.root,
                check=False,
            )

            if result.returncode != 0:
                return f"Ошибка Git: {result.stderr}"

            if result.stdout.strip():
                return result.stdout
            return "Команда выполнена успешно, вывод пуст."
        except subprocess.SubprocessError as e:
            return f"Критическая ошибка при выполнении git: {e}"

    @register_tool(
        "показывает статус репозитория (какие файлы изменены, удалены или не отслеживаются).",
        schema=GitStatusSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_status(self) -> str:
        """Возвращает вывод git status."""
        return self._run_git(["status", "-s"])

    @register_tool(
        "показывает детальные изменения в коде (diff). Полезно перед коммитом.",
        schema=GitDiffSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_diff(self, path: str | None = None) -> str:
        """Возвращает вывод git diff."""
        args = ["diff"]
        if path:
            args.append(path)
        return self._run_git(args)

    @register_tool(
        "показать изменения в staged файлах (git diff --staged).",
        schema=GitDiffStagedSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_diff_staged(self, path: str | None = None) -> str:
        """Возвращает вывод git diff --staged."""
        args = ["diff", "--staged"]
        if path:
            args.append(path)
        return self._run_git(args)

    @register_tool(
        "добавляет файлы в индекс (staging area) для последующего коммита.",
        schema=GitAddSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_add(self, path: str) -> str:
        """Выполняет git add."""
        return self._run_git(["add", path])

    @register_tool(
        "создает коммит с указанным сообщением.",
        schema=GitCommitSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_commit(self, message: str) -> str:
        """Выполняет git commit."""
        return self._run_git(["commit", "-m", message])

    @register_tool(
        "показывает историю коммитов.",
        schema=GitLogSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_log(self, limit: int = 10) -> str:
        """Выполняет git log."""
        return self._run_git(["log", f"-n {limit}", "--oneline"])

    @register_tool(
        "показывает список веток или создает новую.",
        schema=GitBranchSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_branch(self, name: str | None = None) -> str:
        """Выполняет git branch."""
        args = ["branch"]
        if name:
            args.append(name)
        return self._run_git(args)

    @register_tool(
        "переключает ветку или восстанавливает файл из индекса.",
        schema=GitCheckoutSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_checkout(self, target: str) -> str:
        """Выполняет git checkout."""
        return self._run_git(["checkout", target])

    @register_tool(
        "показывает детали конкретного коммита.",
        schema=GitShowSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_show(self, commit_hash: str) -> str:
        """Выполняет git show."""
        return self._run_git(["show", commit_hash])

    @register_tool(
        "управляет временным хранилищем изменений (stash).",
        schema=GitStashSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_stash(self, action: str) -> str:
        """Выполняет git stash."""
        return self._run_git(["stash", action])

    @register_tool(
        "сливает указанную ветку в текущую.",
        schema=GitMergeSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def git_merge(self, branch: str) -> str:
        """Выполняет git merge."""
        return self._run_git(["merge", branch])

    @register_tool(
        "показывает историю изменений по строкам файла (git blame).",
        schema=GitBlameSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_blame(self, path: str) -> str:
        """Выполняет git blame в читаемом формате."""
        try:
            result = subprocess.run(
                ["git", "blame", "--porcelain", path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.fs.root,
                check=False,
            )

            if result.returncode != 0:
                return f"Ошибка Git: {result.stderr}"

            lines = result.stdout.splitlines()
            blame_info: dict[int, dict[str, Any]] = {}
            current_line: int | None = None

            for line in lines:
                if line.startswith("^"):
                    continue
                parts = line.split()
                if len(parts) >= 3 and len(parts[0]) == 40:
                    try:
                        orig_line = int(parts[1])
                        current_line = orig_line
                        blame_info[current_line] = {
                            "commit": parts[0][:7],
                            "author": "",
                            "summary": "",
                            "content": "",
                        }
                    except ValueError:
                        pass
                elif line.startswith("author ") and current_line is not None:
                    blame_info[current_line]["author"] = line[7:]
                elif line.startswith("summary ") and current_line is not None:
                    blame_info[current_line]["summary"] = line[8:]
                elif line.startswith("\t") and current_line is not None:
                    blame_info[current_line]["content"] = line[1:]

            output_lines = []
            for line_num in sorted(blame_info.keys()):
                info = blame_info[line_num]
                summary = info["summary"]
                output_lines.append(
                    f"[{info['commit']}] {info['author']} "
                    f"({summary}): {info['content']}"
                )

            return "\n".join(output_lines)
        except subprocess.SubprocessError as e:
            return f"Критическая ошибка при выполнении git blame: {e}"

    @register_tool(
        "показывает историю изменений конкретного файла.",
        schema=GitLogFileSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def git_log_file(self, path: str, limit: int = 10) -> str:
        """Выполняет git log для конкретного файла."""
        return self._run_git(["log", f"-n {limit}", "--oneline", "--", path])

    @register_tool(
        "возвращает имя текущей активной ветки.",
        schema=GitCurrentBranchSchema,
    )
    def git_current_branch(self) -> str:
        """Возвращает текущую ветку."""
        return self._run_git(["branch", "--show-current"])

    @register_tool(
        "поиск коммитов по тексту в сообщении (git log --grep).",
        schema=GitSearchCommitsSchema,
    )
    def git_search_commits(self, query: str, limit: int = 10) -> str:
        """Ищет коммиты по сообщению."""
        return self._run_git(["log", f"-n {limit}", "--oneline", "--grep", query])
