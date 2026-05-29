"""Базовый класс для специализированных агентов."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vad_code.config import settings
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_providers import BaseLLMProvider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.core.memory import ConversationMemory


class AgentType(Enum):
    """Типы специализированных агентов."""

    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    GENERAL = "general"


@dataclass
class AgentCapability:
    """Описание способности агента."""

    name: str
    description: str
    priority: float = 1.0  # Приоритет для маршрутизации (0.0 - 1.0)
    keywords: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Абстрактный базовый класс для специализированных агентов.

    Каждый специализированный агент наследуется от этого класса
    и реализует свои методы для обработки задач своей области.
    """

    def __init__(
        self,
        agent_type: AgentType,
        llm_client: BaseLLMProvider,
        executor: ToolExecutor,
        tokenizer: Tokenizer,
        system_prompt: str,
    ) -> None:
        """
        Инициализация специализированного агента.

        :param agent_type: Тип агента
        :param llm_client: Провайдер LLM
        :param executor: Исполнитель инструментов
        :param tokenizer: Токенизатор
        :param system_prompt: Системный промпт для агента
        """
        self.agent_type = agent_type
        self.llm_client = llm_client
        self.executor = executor
        self.tokenizer = tokenizer
        self.system_prompt = system_prompt
        self.memory = ConversationMemory(tokenizer, self.system_prompt)

        # Статистика агента
        self.stats = {
            "tasks_completed": 0,
            "errors": 0,
            "total_tokens": 0,
            "avg_response_time_ms": 0,
        }

        # Способности агента
        self.capabilities: list[AgentCapability] = []
        self._setup_capabilities()

    @abstractmethod
    def _setup_capabilities(self) -> None:
        """Настройка способностей агента. Должен быть переопределен в подклассах."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Возвращает системный промпт для агента."""
        ...

    @abstractmethod
    async def handle_task(self, task: str, context: dict[str, Any] | None = None) -> str:
        """
        Обрабатывает задачу в своей области.

        :param task: Описание задачи
        :param context: Контекст задачи (файлы, параметры и т.д.)
        :return: Результат выполнения
        """
        ...

    def can_handle(self, task: str) -> float:
        """
        Оценивает, насколько агент подходит для задачи.

        :param task: Описание задачи
        :return: Оценка от 0.0 до 1.0
        """
        score = 0.0
        task_lower = task.lower()

        for capability in self.capabilities:
            for keyword in capability.keywords:
                if keyword.lower() in task_lower:
                    score = max(score, capability.priority)

        return min(score, 1.0)

    def get_info(self) -> dict[str, Any]:
        """Возвращает информацию об агенте."""
        return {
            "type": self.agent_type.value,
            "capabilities": [
                {"name": c.name, "description": c.description}
                for c in self.capabilities
            ],
            "stats": self.stats.copy(),
        }

    async def close(self) -> None:
        """Освобождает ресурсы агента."""
        # Подклассы могут переопределить для дополнительной очистки
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.agent_type.value}>"
