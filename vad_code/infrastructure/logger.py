"""Модуль логирования."""
import json
import logging
import sys
from logging.handlers import RotatingFileHandler


class JsonFormatter(logging.Formatter):
    """Форматировщик логов в JSON для удобного парсинга в продакшене."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def setup_logger() -> logging.Logger:
    """Настраивает и возвращает логгер."""
    logger = logging.getLogger("ai_os")

    # Предотвращаем дублирование хендлеров при повторных вызовах
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Формат для консоли: читаемый человеком
    console_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    # Формат для файла: JSON (структурированный)
    file_formatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S")

    # Вывод в консоль (только INFO и выше, чтобы не заспамить пользователя)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Запись всех деталей в файл с ротацией:
    # maxBytes=5*1024*1024 (5 MB), backupCount=5 (храним до 5 старых файлов)
    file_handler = RotatingFileHandler(
        "agent.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


log = setup_logger()
