"""Система коммуникации между агентами."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from vad_code.infrastructure.logger import log


class MessageType(Enum):
    """Типы сообщений между агентами."""

    TASK = "task"  # Задача для агента
    RESULT = "result"  # Результат выполнения
    REQUEST = "request"  # Запрос информации
    RESPONSE = "response"  # Ответ на запрос
    ERROR = "error"  # Ошибка
    BROADCAST = "broadcast"  # Рассылка всем агентам


@dataclass
class AgentMessage:
    """Сообщение между агентами."""

    message_type: MessageType
    content: str
    sender: str = "orchestrator"  # ID отправителя
    receiver: str | None = None  # ID получателя (None = broadcast)
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = uuid.uuid4().hex[:8]


class CommunicationBus:
    """Шина коммуникации для обмена сообщениями между агентами.

    Поддерживает:
    - Точечные сообщения (один к одному)
    - Broadcast (один ко всем)
    - Асинхронную доставку
    - Очереди сообщений для каждого агента
    """

    def __init__(self) -> None:
        # Очереди сообщений для каждого агента
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        # История сообщений
        self._history: list[AgentMessage] = []
        # Максимальный размер истории
        self._max_history = 1000
        # Глобальная блокировка для thread-safety
        self._lock = asyncio.Lock()

    def register_agent(self, agent_id: str) -> None:
        """Регистрирует агента в шине коммуникации."""
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=100)
            log.debug(f"📡 Агент {agent_id} зарегистрирован в шине")

    def unregister_agent(self, agent_id: str) -> None:
        """Удаляет агента из шины коммуникации."""
        if agent_id in self._queues:
            del self._queues[agent_id]
            log.debug(f"📡 Агент {agent_id} удален из шины")

    async def send(
        self,
        message_type: MessageType,
        content: str,
        sender: str,
        receiver: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """
        Отправляет сообщение.

        :param message_type: Тип сообщения
        :param content: Содержимое
        :param sender: ID отправителя
        :param receiver: ID получателя (None = broadcast)
        :param metadata: Дополнительные данные
        :return: Отправленное сообщение
        """
        async with self._lock:
            message = AgentMessage(
                message_type=message_type,
                content=content,
                sender=sender,
                receiver=receiver,
                metadata=metadata or {},
            )

            # Сохраняем в историю
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            if receiver:
                # Точечное сообщение
                if receiver in self._queues:
                    await self._queues[receiver].put(message)
                    log.debug(
                        f"📨 [{message_type.value}] {sender} -> {receiver} "
                        f"(task={message.task_id})"
                    )
                else:
                    log.warning(f"⚠️ Агент {receiver} не найден")
            else:
                # Broadcast всем агентам
                for agent_id in self._queues:
                    if agent_id != sender:
                        await self._queues[agent_id].put(message)
                log.debug(
                    f"📢 [{message_type.value}] {sender} -> ALL "
                    f"(task={message.task_id})"
                )

            return message

    async def receive(self, agent_id: str, timeout: float = 5.0) -> AgentMessage | None:
        """
        Получает сообщение для агента.

        :param agent_id: ID агента
        :param timeout: Таймаут в секундах
        :return: Сообщение или None
        """
        if agent_id not in self._queues:
            return None

        try:
            message = await asyncio.wait_for(
                self._queues[agent_id].get(), timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None

    async def receive_all(self, agent_id: str) -> list[AgentMessage]:
        """Получает все ожидающие сообщения для агента."""
        messages: list[AgentMessage] = []
        if agent_id not in self._queues:
            return messages

        while not self._queues[agent_id].empty():
            try:
                message = self._queues[agent_id].get_nowait()
                messages.append(message)
            except asyncio.QueueEmpty:
                break

        return messages

    def get_history(
        self,
        agent_id: str | None = None,
        message_type: MessageType | None = None,
        limit: int = 100,
    ) -> list[AgentMessage]:
        """
        Получает историю сообщений.

        :param agent_id: Фильтр по агенту
        :param message_type: Фильтр по типу
        :param limit: Максимальное количество
        :return: Список сообщений
        """
        filtered = self._history

        if agent_id:
            filtered = [
                m for m in filtered if m.sender == agent_id or m.receiver == agent_id
            ]

        if message_type:
            filtered = [m for m in filtered if m.message_type == message_type]

        return filtered[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику шины."""
        total_messages = len(self._history)
        by_type: dict[str, int] = {}
        for msg in self._history:
            type_name = msg.message_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total_messages": total_messages,
            "registered_agents": len(self._queues),
            "by_type": by_type,
            "queue_sizes": {
                aid: q.qsize() for aid, q in self._queues.items()
            },
        }

    async def clear(self) -> None:
        """Очищает все очереди и историю."""
        async with self._lock:
            for queue in self._queues.values():
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
            self._history.clear()
            log.info("🧹 Шина коммуникации очищена")
