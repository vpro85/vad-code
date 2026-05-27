"""
Инструменты для выполнения команд.
"""
import shlex
import subprocess

from ..infrastructure.file_system import FileSystemService
from .permissions import register_tool, ToolRiskLevel
from .schemas import RunCommandSchema, RunTestsSchema, FormatCodeSchema

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

    @register_tool(
        "запускает тесты в указанном пути с подробным выводом",
        schema=RunTestsSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def run_tests(self, path: str = ".", verbose: bool = True, timeout: int = 120) -> str:
        """Запускает pytest в указанном пути."""
        try:
            args = ["pytest", path]
            if verbose:
                args.append("-v")
            args.extend(["--tb=short", "-x"])

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
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

            return output if output.strip() else "Тесты выполнены, вывод пуст."

        except subprocess.TimeoutExpired:
            return f"Ошибка: время выполнения тестов истекло (таймаут {timeout}с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при запуске тестов: {e}"

    @register_tool(
        "форматирует код с помощью black, autopep8 или isort",
        schema=FormatCodeSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def format_code(self, path: str = ".", tool: str = "black", check_only: bool = False) -> str:
        """Форматирует код с помощью указанного инструмента."""
        if tool not in ("black", "autopep8", "isort"):
            return f"Ошибка: неизвестный инструмент '{tool}'. Используйте: black, autopep8, isort"

        try:
            args = [tool, path]
            if check_only:
                if tool == "black":
                    args.append("--check")
                elif tool == "autopep8":
                    args.append("--diff")
                # isort --check-only
                else:
                    args.insert(1, "--check-only")

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

            if check_only:
                if exit_code == 0:
                    return f"Код уже отформатирован ({tool})."
                return f"Код требует форматирования ({tool}):\n{stdout}{stderr}"

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"

            return output if output.strip() else f"Форматирование завершено ({tool})."

        except FileNotFoundError:
            return f"Ошибка: инструмент '{tool}' не установлен. Установите его через pip."
        except subprocess.TimeoutExpired:
            return f"Ошибка: время форматирования истекло (таймаут 60с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при форматировании кода: {e}"
