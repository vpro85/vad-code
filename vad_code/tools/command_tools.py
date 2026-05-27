"""
Инструменты для выполнения команд.
"""
import shlex
import subprocess

from ..infrastructure.file_system import FileSystemService
from .permissions import register_tool, ToolRiskLevel
from .schemas import RunCommandSchema

_ALLOWED_COMMANDS = {"pytest", "pylint", "flake8", "mypy"}


class CommandTools:
    """Инструменты для выполнения команд в терминале."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    @register_tool(
        "запускает тесты или другие разрешенные команды в терминале",
        schema=RunCommandSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def run_command(self, command: str) -> str:
        """Запускает команду в терминале."""
        try:
            args = shlex.split(command)
            if not args:
                return "Ошибка: пустая команда."

            base_cmd = args[0]
            if base_cmd not in _ALLOWED_COMMANDS:
                return (
                    f"Ошибка: команда '{base_cmd}' запрещена. "
                    f"Разрешены только: {', '.join(_ALLOWED_COMMANDS)}"
                )

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.fs.root,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"

            return output if output.strip() else "Команда выполнена, вывод пуст."

        except subprocess.TimeoutExpired:
            return "Ошибка: время выполнения команды истекло (таймаут 60с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при выполнении команды: {e}"
