"""
Модуль безопасности для выполнения команд.
Проверка на опасные паттерны, белый/черный список команд.
"""

import re
from typing import Optional

from vad_code.infrastructure.logger import log

# Белый список разрешенных команд
ALLOWED_COMMANDS = {
    # Тестирование
    "pytest",
    "unittest",
    "coverage",
    # Линтеры и статический анализ
    "pylint",
    "flake8",
    "mypy",
    "ruff",
    "black",
    "isort",
    "autopep8",
    # Git
    "git",
    # Python
    "python",
    "python3",
    "pip",
    "pip3",
    # Утилиты
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "du",
    "df",
    "tree",
    "file",
    "stat",
    # Сетевые утилиты (только чтение)
    "curl",
    "wget",
    # Компиляция/сборка
    "make",
    "cmake",
    "npm",
    "yarn",
    # Docker (только чтение)
    "docker",
    "docker-compose",
}

# Черный список запрещенных команд (всегда запрещены)
BLACKLISTED_COMMANDS = {
    "rm",
    "rmdir",
    "del",
    "erase",
    "sudo",
    "su",
    "chmod",
    "chown",
    "mkfs",
    "dd",
    "fdisk",
    "parted",
    "shutdown",
    "reboot",
    "poweroff",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "brew",  # системные пакеты
    "curl",
    "wget",  # могут скачивать вредоносное ПО
}

# Опасные паттерны в командах
DANGEROUS_PATTERNS = [
    (r"\brm\s+-[a-zA-Z]*r", "Рекурсивное удаление (rm -r/-rf)"),
    (r"\bsudo\b", "Использование sudo"),
    (r"\bsu\b", "Переключение пользователя"),
    (r";\s*rm\b", "Удаление после точки с запятой"),
    (r"&&\s*rm\b", "Удаление после &&"),
    (r"\|\s*rm\b", "Удаление через pipe"),
    (r">\s*/dev/", "Запись в устройство"),
    (r"\$\(.*\)", "Подстановка команды $()"),
    (r"`.*`", "Подстановка команды ``"),
    (r"\beval\b", "Выполнение eval"),
    (r"\bexec\b", "Выполнение exec"),
    (r"\bmkfs\b", "Форматирование файловой системы"),
    (r"\bdd\s+if=/dev/", "Запись в устройство через dd"),
    (r"\bchmod\s+[0-7]*777", "chmod 777"),
    (r"\bchown\s+root", "Изменение владельца на root"),
    (r"\bshutdown\b", "Выключение системы"),
    (r"\breboot\b", "Перезагрузка системы"),
    (r"\bformat\b", "Форматирование диска"),
    (r"\bdel\s+/q", "Быстрое удаление в Windows"),
    (r"\berase\b", "Стирание данных"),
    (r"/\s+-rf\b", "Аргумент -rf"),
    (
        r"\bapt\s+(get\s+)?(install|remove|purge)",
        "Установка/удаление системных пакетов",
    ),
    (r"\byum\s+(install|remove)", "Установка/удаление через yum"),
    (r"\b(dnf|pacman|brew)\s+(install|remove|delete)", "Установка/удаление пакетов"),
]


class CommandSecurityError(Exception):
    """Ошибка безопасности при выполнении команды."""

    pass


class CommandValidator:
    """
    Валидатор команд для проверки безопасности.

    Проверяет:
    - Белый список разрешенных команд
    - Черный список запрещенных команд
    - Опасные паттерны в аргументах
    - Ограничения по времени выполнения
    """

    def __init__(
        self,
        allowed_commands: Optional[set] = None,
        max_timeout: int = 300,  # 5 минут максимум
        max_output_size: int = 1_000_000,  # 1MB
    ):
        self.allowed_commands = allowed_commands or ALLOWED_COMMANDS
        self.max_timeout = max_timeout
        self.max_output_size = max_output_size

    def validate(self, command: str) -> tuple[bool, str]:
        """
        Проверяет безопасность команды.

        Args:
            command: Команда для проверки.

        Returns:
            Кортеж (безопасно, сообщение).
        """
        # Проверка на пустую команду
        if not command or not command.strip():
            return False, "Пустая команда."

        # Проверка на опасные паттерны
        dangerous_match = self._check_dangerous_patterns(command)
        if dangerous_match:
            return False, f"Обнаружен опасный паттерн: {dangerous_match}"

        # Извлекаем базовую команду
        base_cmd = self._extract_base_command(command)
        if not base_cmd:
            return False, "Не удалось определить команду."

        # Проверка черного списка
        if base_cmd in BLACKLISTED_COMMANDS:
            return False, f"Команда '{base_cmd}' запрещена (черный список)."

        # Проверка белого списка
        if base_cmd not in self.allowed_commands:
            return False, (
                f"Команда '{base_cmd}' не в белом списке. "
                f"Разрешены: {', '.join(sorted(self.allowed_commands))}"
            )

        return True, "Команда безопасна."

    def _check_dangerous_patterns(self, command: str) -> Optional[str]:
        """
        Проверяет команду на наличие опасных паттернов.

        Args:
            command: Команда для проверки.

        Returns:
            Описание опасного паттерна или None.
        """
        for pattern, description in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                log.warning(
                    "⚠️ Dangerous pattern detected: %s in '%s'", description, command
                )
                return description
        return None

    def _extract_base_command(self, command: str) -> Optional[str]:
        """
        Извлекает базовую команду из строки.

        Args:
            command: Строка команды.

        Returns:
            Имя базовой команды или None.
        """
        try:
            import shlex

            args = shlex.split(command)
            if args:
                # Убираем путь, оставляем только имя команды
                return args[0].split("/")[-1]
        except ValueError:
            pass
        return None

    def validate_timeout(self, timeout: int) -> tuple[bool, str]:
        """
        Проверяет время выполнения команды.

        Args:
            timeout: Время в секундах.

        Returns:
            Кортеж (допустимо, сообщение).
        """
        if timeout <= 0:
            return False, "Время выполнения должно быть положительным."
        if timeout > self.max_timeout:
            return False, f"Время выполнения превышает максимум ({self.max_timeout}с)."
        return True, "Время выполнения допустимо."


# Глобальный экземпляр
command_validator = CommandValidator()
