import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("ai_os")
    logger.setLevel(logging.DEBUG)

    # Формат: Время | Уровень | Сообщение
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    # Вывод в консоль (только INFO и выше, чтобы не заспамить пользователя)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Запись всех деталей в файл с ротацией:
    # maxBytes=5*1024*1024 (5 MB), backupCount=5 (храним до 5 старых файлов)
    file_handler = RotatingFileHandler(
        "agent.log", 
        maxBytes=5 * 1024 * 1024, 
        backupCount=5, 
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


log = setup_logger()