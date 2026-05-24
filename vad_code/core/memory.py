"""
Модуль управления памятью агента
"""
from typing import Any

from vad_code.config import settings
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer


class ConversationMemory:
    """Класс для управления историей диалога, подсчета токенов и обрезки контекста."""

    def __init__(self, tokenizer: Tokenizer, system_prompt: str) -> None:
        self.tokenizer = tokenizer
        self.system_prompt = system_prompt
        self.history: list[dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        """Добавляет сообщение в историю."""
        self.history.append({"role": role, "content": content})

    def reset(self) -> None:
        """Очищает историю сообщений."""
        self.history = []
        log.info("🧹 История сообщений очищена.")

    def get_messages(self) -> list[dict[str, Any]]:
        """Возвращает полный список сообщений для отправки в LLM (включая системный промпт)."""
        return [{"role": "system", "content": self.system_prompt}] + self.history

    def trim(self) -> None:
        """Обрезает историю, соблюдая лимиты сообщений и токенов."""
        # 1. Лимит по количеству сообщений (сохраняем первое сообщение сессии)
        if len(self.history) > settings.max_history_messages:
            first_msg = self.history[0]
            recent = self.history[-(settings.max_history_messages - 1):]
            self.history = [first_msg] + recent

        # 2. Лимит по количеству токенов
        system_tokens = self.tokenizer.count_tokens(self.system_prompt)
        
        def get_current_total() -> int:
            return system_tokens + self.tokenizer.count_messages_tokens(self.history)

        total_tokens = get_current_total()
        log.warning(f"Current history size: {total_tokens} tokens, {len(self.history)} messages")

        if total_tokens <= settings.max_context_tokens:
            return

        # 3. Попытка удалить пары: [assistant (tool call)] + [user (observation)]
        idx = 1
        while total_tokens > settings.max_context_tokens and idx + 1 < len(self.history):
            msg_a = self.history[idx]
            msg_b = self.history[idx + 1]
            
            if (
                msg_a["role"] == "assistant"
                and msg_b["role"] == "user"
                and msg_b["content"].startswith("OBSERVATION:")
            ):
                pair_tokens = (self.tokenizer.count_tokens(msg_a["role"]) +
                               self.tokenizer.count_tokens(msg_a["content"]) +
                               self.tokenizer.count_tokens(msg_b["role"]) +
                               self.tokenizer.count_tokens(msg_b["content"]))
                del self.history[idx : idx + 2]
                total_tokens -= pair_tokens
            else:
                idx += 1

        # 4. Fallback: Удаляем самые старые сообщения (кроме первого)
        if total_tokens > settings.max_context_tokens and len(self.history) > 1:
            while total_tokens > settings.max_context_tokens and len(self.history) > 1:
                removed_msg = self.history.pop(1)
                removed_tokens = (self.tokenizer.count_tokens(removed_msg["role"]) +
                                  self.tokenizer.count_tokens(removed_msg["content"]))
                total_tokens -= removed_tokens
                log.info("🗑️ Удалено старое сообщение из истории для экономии контекста.")
