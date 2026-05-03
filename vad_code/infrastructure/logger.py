import logging
import sys


def setup_logger():
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

    # Запись всех деталей в файл (DEBUG и выше)
    file_handler = logging.FileHandler("agent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


log = setup_logger()
