"""Мульти-агентная архитектура.

Модуль содержит:
- BaseAgent — абстрактный класс для специализированных агентов
- Orchestrator — координатор для распределения задач
- AgentPool — пул агентов для параллельного выполнения
- Communication — система обмена сообщениями между агентами
- SpecializedAgents — конкретные реализации агентов
"""

from vad_code.core.multi_agent.base_agent import BaseAgent, AgentType, AgentCapability
from vad_code.core.multi_agent.orchestrator import Orchestrator, TaskResult
from vad_code.core.multi_agent.agent_pool import AgentPool, WorkerConfig
from vad_code.core.multi_agent.communication import (
    AgentMessage,
    MessageType,
    CommunicationBus,
)
from vad_code.core.multi_agent.specialized_agents import (
    CodeReviewAgent,
    TestingAgent,
    DocumentationAgent,
    SecurityAgent,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentType",
    "AgentCapability",
    # Orchestrator
    "Orchestrator",
    "TaskResult",
    # Pool
    "AgentPool",
    "WorkerConfig",
    # Communication
    "AgentMessage",
    "MessageType",
    "CommunicationBus",
    # Specialized agents
    "CodeReviewAgent",
    "TestingAgent",
    "DocumentationAgent",
    "SecurityAgent",
]
