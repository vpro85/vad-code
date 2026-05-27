"""
Инструменты для выполнения команд.
"""
import shlex
import subprocess

from ..infrastructure.file_system import FileSystemService
from ..infrastructure.command_security import command_validator
from .permissions import register_tool, ToolRiskLevel
from .schemas import RunCommandSchema, RunTestsSchema, FormatCodeSchema, InstallPackageSchema


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
        # Проверка безопасности команды
        is_safe, message = command_validator.validate(command)
        if not is_safe:
            return f"Ошибка безопасности: {message}"

        try:
            args = shlex.split(command)
            if not args:
                return "Ошибка: пустая команда."

            # Проверка таймаута (по умолчанию 60с, максимум 300с)
            timeout = 60
            is_timeout_valid, _ = command_validator.validate_timeout(timeout)
            if not is_timeout_valid:
                return "Ошибка: время выполнения превышает допустимый лимит."

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

            # Ограничение размера вывода
            max_size = command_validator.max_output_size
            if len(stdout) > max_size:
                stdout = stdout[:max_size] + "\n... [вывод обрезан]"
            if len(stderr) > max_size:
                stderr = stderr[:max_size] + "\n... [вывод обрезан]"

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"

            return output if output.strip() else "Команда выполнена, вывод пуст."

        except subprocess.TimeoutExpired:
            return f"Ошибка: время выполнения команды истекло (таймаут {timeout}с)."
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

    @register_tool(
        "устанавливает Python-пакет через pip",
        schema=InstallPackageSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def install_package(self, package: str, upgrade: bool = False, user_install: bool = False) -> str:
        """Устанавливает или обновляет Python-пакет."""
        try:
            args = ["pip", "install"]
            if upgrade:
                args.append("--upgrade")
            if user_install:
                args.append("--user")
            args.append(package)

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.fs.root,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            if exit_code == 0:
                return f"Пакет '{package}' успешно установлен.\n{stdout}"

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"
            return output

        except subprocess.TimeoutExpired:
            return "Ошибка: время установки пакета истекло (таймаут 120с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при установке пакета: {e}"
