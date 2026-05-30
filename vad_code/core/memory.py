"""
Модуль управления памятью агента
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vad_code.config import settings
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer


@dataclass
class MemoryConfig:
    """Конфигурация памяти."""

    max_history_messages: int = 20
    max_context_tokens: int = 30000
    enable_smart_trim: bool = True
    enable_compression: bool = True
    compression_threshold: int = 15
    priority_keep_messages: int = 3


class SmartConversationMemory:
    """Улучшенная память с умным управлением контекстом."""

    def __init__(
        self,
        tokenizer: Tokenizer,
        system_prompt: str,
        config: MemoryConfig | None = None,
    ) -> None:
        self.tokenizer = tokenizer
        self.system_prompt = system_prompt
        self.config = config or MemoryConfig(
            max_history_messages=settings.max_history_messages,
            max_context_tokens=settings.max_context_tokens,
        )
        self.history: list[dict[str, Any]] = []
        self._compressed_facts: list[str] = []

    def add_message(self, role: str, content: str, priority: bool = False) -> None:
        """Добавляет сообщение в историю."""
        msg = {"role": role, "content": content}
        if priority:
            msg["priority"] = priority
        self.history.append(msg)

    def reset(self) -> None:
        """Очищает историю сообщений."""
        self.history = []
        self._compressed_facts = []
        log.info("История сообщений очищена.")

    def get_messages(self) -> list[dict[str, Any]]:
        """Возвращает полный список сообщений для отправки в LLM."""
        messages = [{"role": "system", "content": self.system_prompt}]

        if self._compressed_facts:
            facts_text = "\n".join(self._compressed_facts)
            messages.append({
                "role": "system",
                "content": f"Ключевые факты из предыдущего контекста:\n{facts_text}",
            })

        for msg in self.history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return messages

    def trim(self) -> None:
        """Обрезает историю, соблюдая лимиты сообщений и токенов."""
        max_messages = settings.max_history_messages
        max_tokens = settings.max_context_tokens

        if len(self.history) > max_messages:
            self._trim_by_message_count(max_messages)

        system_tokens = self.tokenizer.count_tokens(self.system_prompt)

        def get_current_total() -> int:
            return system_tokens + self.tokenizer.count_messages_tokens(
                [{"role": m["role"], "content": m["content"]} for m in self.history]
            )

        total_tokens = get_current_total()
        log.debug(
            "Current history size: %d tokens, %d messages",
            total_tokens,
            len(self.history),
        )

        if total_tokens <= max_tokens:
            return

        if self.config.enable_compression and len(self.history) > self.config.compression_threshold:
            self._compress_old_messages()

        idx = 0
        while total_tokens > max_tokens and idx + 1 < len(self.history):
            msg_a = self.history[idx]
            msg_b = self.history[idx + 1]

            if (
                msg_a["role"] == "assistant"
                and msg_b["role"] == "user"
                and msg_b["content"].startswith("OBSERVATION:")
            ):
                pair_tokens = (
                    self.tokenizer.count_tokens(msg_a["role"])
                    + self.tokenizer.count_tokens(msg_a["content"])
                    + self.tokenizer.count_tokens(msg_b["role"])
                    + self.tokenizer.count_tokens(msg_b["content"])
                )
                del self.history[idx : idx + 2]
                total_tokens -= pair_tokens
            else:
                idx += 1

        if total_tokens > max_tokens and len(self.history) > 1:
            while total_tokens > max_tokens and len(self.history) > 1:
                removed = False
                for i in range(1, len(self.history)):
                    if not self.history[i].get("priority", False):
                        removed_msg = self.history.pop(i)
                        removed_tokens = self.tokenizer.count_tokens(
                            removed_msg["role"]
                        ) + self.tokenizer.count_tokens(removed_msg["content"])
                        total_tokens -= removed_tokens
                        log.info(
                            "Удалено старое сообщение из истории для экономии контекста."
                        )
                        removed = True
                        break
                if not removed:
                    break

    def _trim_by_message_count(self, max_messages: int) -> None:
        """Обрезает историю по количеству сообщений, сохраняя приоритетные."""
        priority_msgs = [m for m in self.history if m.get("priority", False)]
        non_priority_msgs = [m for m in self.history if not m.get("priority", False)]

        available_slots = max_messages - len(priority_msgs)
        if available_slots <= 0:
            self.history = priority_msgs
            return

        # Сохраняем первое сообщение (контекст начала диалога)
        first_msg = self.history[0]
        keep_candidates = []
        if not first_msg.get("priority", False):
            keep_candidates.append(first_msg)
            available_slots -= 1

        # Заполняем оставшиеся слоты самыми свежими сообщениями
        recent = non_priority_msgs[-available_slots:] if available_slots > 0 else []
        self.history = priority_msgs + keep_candidates + recent

    def _compress_old_messages(self) -> None:
        """Сжимает старые сообщения, сохраняя ключевые факты."""
        if len(self.history) <= self.config.compression_threshold:
            return

        old_count = len(self.history) - self.config.compression_threshold
        old_messages = self.history[:old_count]
        recent_messages = self.history[old_count:]

        facts = self._extract_facts(old_messages)
        self._compressed_facts.extend(facts)

        if facts:
            summary = "[Сжатый контекст: ключевые факты сохранены]"
            self.history = [{"role": "system", "content": summary, "priority": True}] + recent_messages
            log.info("Сжато %d сообщений, сохранено %d фактов", old_count, len(facts))

    def _extract_facts(self, messages: list[dict[str, Any]]) -> list[str]:
        """Извлекает ключевые факты из сообщений."""
        facts: list[str] = []

        for msg in messages:
            content = msg["content"]

            if msg["role"] == "assistant" and "tool" in content:
                try:
                    import json5
                    call_data = json5.loads(content)
                    if "arguments" in call_data and "path" in call_data["arguments"]:
                        facts.append(f"Файл: {call_data['arguments']['path']}")
                except Exception:
                    pass

            if msg["role"] == "user" and content.startswith("OBSERVATION:"):
                obs = content[len("OBSERVATION:"):].strip()
                if len(obs) < 200:
                    facts.append(f"Результат: {obs[:100]}...")

        return facts[:10]

    def to_text(self) -> str:
        """Возвращает текстовое представление истории для сохранения в файл."""
        lines = []
        for msg in self.history:
            role = msg["role"].upper()
            content = msg["content"]
            lines.append(f"[{role}] {content}")
        return "\n---\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику памяти."""
        system_tokens = self.tokenizer.count_tokens(self.system_prompt)
        history_tokens = self.tokenizer.count_messages_tokens(
            [{"role": m["role"], "content": m["content"]} for m in self.history]
        )

        return {
            "total_messages": len(self.history),
            "total_tokens": system_tokens + history_tokens,
            "system_tokens": system_tokens,
            "history_tokens": history_tokens,
            "compressed_facts": len(self._compressed_facts),
            "priority_messages": sum(1 for m in self.history if m.get("priority", False)),
        }


# Backward compatibility alias
ConversationMemory = SmartConversationMemory
