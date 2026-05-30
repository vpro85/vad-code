"""
Цветной вывод для CLI.
"""

import sys
from typing import TextIO


class Colors:
    """ANSI цвета для терминала."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Цвета
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Фоны
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def supported() -> bool:
        """Проверяет поддержку цветов в терминале."""
        return sys.stdout.isatty()


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Окрашивает текст."""
    if not Colors.supported():
        return text
    prefix = Colors.BOLD + color if bold else color
    return f"{prefix}{text}{Colors.RESET}"


def success(text: str) -> str:
    """Зеленый текст."""
    return colorize(text, Colors.GREEN, bold=True)


def error(text: str) -> str:
    """Красный текст."""
    return colorize(text, Colors.RED, bold=True)


def warning(text: str) -> str:
    """Желтый текст."""
    return colorize(text, Colors.YELLOW, bold=True)


def info(text: str) -> str:
    """Синий текст."""
    return colorize(text, Colors.BLUE)


def debug(text: str) -> str:
    """Серый текст."""
    return colorize(text, Colors.DIM)


def tool_call(text: str) -> str:
    """Фиолетовый для tool calls."""
    return colorize(text, Colors.MAGENTA)


def observation(text: str) -> str:
    """Голубой для наблюдений."""
    return colorize(text, Colors.CYAN)


def print_colored(
    text: str,
    color: str,
    bold: bool = False,
    file: TextIO | None = None,
) -> None:
    """Печатает окрашенный текст."""
    print(colorize(text, color, bold), file=file)
