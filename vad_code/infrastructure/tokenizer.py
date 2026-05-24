from typing import Any

from transformers import AutoTokenizer

from vad_code.config import settings


class Tokenizer:
    """
    Класс для токенизации текста с использованием библиотеки transformers.
    Позволяет точно подсчитывать количество токенов для управления контекстным окном LLM.
    """

    def __init__(self) -> None:
        # Загружаем токенизатор для указанной модели
        # use_fast=True используется для ускорения работы
        self.tokenizer = AutoTokenizer.from_pretrained(settings.model_name, use_fast=True)

    def count_tokens(self, text: str) -> int:
        """
        Возвращает количество токенов в строке текста.
        """
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def count_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Приблизительно подсчитывает количество токенов в списке сообщений.
        Учитывает роли и содержимое.
        """
        total = 0
        for msg in messages:
            # Считаем токены для роли и контента
            total += self.count_tokens(msg['role'])
            total += self.count_tokens(msg['content'])
        return total
