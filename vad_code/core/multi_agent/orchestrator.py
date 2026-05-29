"""Оркестратор — координатор для распределения задач между агентами."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from vad_code.core.executor import ToolExecutor
from vad_code.core.multi_agent.base_agent import AgentType, BaseAgent
from vad_code.core.multi_agent.communication import (
    CommunicationBus,
    MessageType,
)
from vad_code.infrastructure.llm_providers import BaseLLMProvider
from vad_code.infrastructure.logger import log
from vad_code.infrastructure.tokenizer import Tokenizer


@dataclass
class TaskResult:
    """Результат выполнения задачи."""

    agent_type: AgentType
    success: bool
    result: str
    execution_time_ms: float
    tokens_used: int = 0
    error: str | None = None


class Orchestrator:
    """Оркестратор — распределяет задачи между специализированными агентами.

    Функции:
    - Анализ задачи и выбор подходящего агента
    - Распределение задач
    - Агрегация результатов
    - Управление жизненным циклом агентов
    """

    def __init__(
        self,
        llm_client: BaseLLMProvider,
        executor: ToolExecutor,
        tokenizer: Tokenizer,
    ) -> None:
        """
        Инициализация оркестратора.

        :param llm_client: Провайдер LLM
        :param executor: Исполнитель инструментов
        :param tokenizer: Токенизатор
        """
        self.llm_client = llm_client
        self.executor = executor
        self.tokenizer = tokenizer
        self.comm_bus = CommunicationBus()

        # Пул агентов
        self._agents: dict[AgentType, BaseAgent] = {}
        self._agent_ids: dict[AgentType, str] = {}

        # Статистика
        self.stats = {
            "tasks_routed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time_ms": 0.0,
        }

        log.info("🎯 Оркестратор инициализирован")

    def create_default_agents(self) -> None:
        """Создает и регистрирует стандартных агентов."""
        from vad_code.core.multi_agent.specialized_agents import (
            CodeReviewAgent,
            TestingAgent,
            DocumentationAgent,
            SecurityAgent,
        )

        agent_configs = [
            (CodeReviewAgent, AgentType.CODE_REVIEW),
            (TestingAgent, AgentType.TESTING),
            (DocumentationAgent, AgentType.DOCUMENTATION),
            (SecurityAgent, AgentType.SECURITY),
        ]

        for agent_class, agent_type in agent_configs:
            agent = agent_class(
                agent_type=agent_type,
                llm_client=self.llm_client,
                executor=self.executor,
                tokenizer=self.tokenizer,
            )
            self.register_agent(agent)

        log.info("🤖 Создано %d специализированных агентов", len(agent_configs))

    def register_agent(self, agent: BaseAgent) -> None:
        """Регистрирует агента в оркестраторе."""
        agent_id = agent.agent_type.value
        self._agents[agent.agent_type] = agent
        self._agent_ids[agent.agent_type] = agent_id
        self.comm_bus.register_agent(agent_id)
        log.info("🤖 Агент зарегистрирован: %s", agent)

    def get_agent(self, agent_type: AgentType) -> BaseAgent | None:
        """Получает агента по типу."""
        return self._agents.get(agent_type)

    def get_all_agents(self) -> list[BaseAgent]:
        """Возвращает всех зарегистрированных агентов."""
        return list(self._agents.values())

    def route_task(self, task: str) -> AgentType:
        """
        Определяет, какой агент лучше всего подходит для задачи.

        :param task: Описание задачи
        :return: Тип выбранного агента
        """
        best_agent: AgentType | None = None
        best_score = 0.0

        for agent in self._agents.values():
            score = agent.can_handle(task)
            if score > best_score:
                best_score = score
                best_agent = agent.agent_type

        # Если ни один специализированный агент не подходит, используем общего
        if best_score < 0.3 or best_agent is None:
            log.debug("🔍 Низкая оценка (%.2f), используем общего агента", best_score)
            return AgentType.GENERAL

        log.info(
            "📍 Задача маршрутизирована -> %s "
            "(оценка: %.2f)",
            best_agent.value,
            best_score,
        )
        return best_agent

    async def execute_task(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        force_agent: AgentType | None = None,
    ) -> TaskResult:
        """
        Выполняет задачу через подходящего агента.

        :param task: Описание задачи
        :param context: Контекст задачи
        :param force_agent: Принудительно использовать конкретного агента
        :return: Результат выполнения
        """
        start_time = time.time()
        self.stats["tasks_routed"] += 1

        # Выбор агента
        if force_agent:
            agent_type = force_agent
        else:
            agent_type = self.route_task(task)

        agent = self._agents.get(agent_type)
        if not agent:
            execution_time = (time.time() - start_time) * 1000
            return TaskResult(
                agent_type=agent_type,
                success=False,
                result="",
                execution_time_ms=execution_time,
                error=f"Агент типа {agent_type.value} не найден",
            )

        try:
            # Отправляем задачу агенту через шину
            await self.comm_bus.send(
                message_type=MessageType.TASK,
                content=task,
                sender="orchestrator",
                receiver=self._agent_ids[agent_type],
                metadata={"context": context},
            )

            # Выполняем задачу
            result = await agent.handle_task(task, context)

            execution_time = (time.time() - start_time) * 1000
            self.stats["tasks_completed"] += 1
            self.stats["total_execution_time_ms"] += execution_time

            # Обновляем статистику агента
            agent.stats["tasks_completed"] += 1

            log.info(
                "✅ Задача выполнена агентом %s "
                "за %.0fms",
                agent_type.value,
                execution_time,
            )

            return TaskResult(
                agent_type=agent_type,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.stats["tasks_failed"] += 1
            self.stats["total_execution_time_ms"] += execution_time
            agent.stats["errors"] += 1

            log.error(
                "❌ Ошибка выполнения задачи агентом %s: %s",
                agent_type.value,
                e,
            )

            return TaskResult(
                agent_type=agent_type,
                success=False,
                result="",
                execution_time_ms=execution_time,
                error=str(e),
            )

    async def execute_parallel(
        self,
        tasks: list[tuple[str, dict[str, Any] | None]],
    ) -> list[TaskResult]:
        """
        Выполняет несколько задач параллельно.

        :param tasks: Список кортежей (задача, контекст)
        :return: Список результатов
        """
        log.info("🚀 Параллельное выполнение %d задач", len(tasks))

        async def _execute(task: str, ctx: dict[str, Any] | None) -> TaskResult:
            return await self.execute_task(task, ctx)

        coroutines = [_execute(task, ctx) for task, ctx in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Обработка исключений
        final_results: list[TaskResult] = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(
                    TaskResult(
                        agent_type=AgentType.GENERAL,
                        success=False,
                        result="",
                        execution_time_ms=0.0,
                        error=str(result),
                    )
                )
            else:
                assert isinstance(result, TaskResult)
                final_results.append(result)

        return final_results

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику оркестратора."""
        agent_stats = {
            agent_type.value: agent.get_info()
            for agent_type, agent in self._agents.items()
        }

        avg_time = (
            self.stats["total_execution_time_ms"] / self.stats["tasks_routed"]
            if self.stats["tasks_routed"] > 0
            else 0
        )

        return {
            "orchestrator": {
                **self.stats,
                "avg_execution_time_ms": round(avg_time, 2),
            },
            "agents": agent_stats,
            "communication": self.comm_bus.get_stats(),
        }

    async def close(self) -> None:
        """Освобождает ресурсы всех агентов."""
        log.info("🔒 Закрытие оркестратора...")
        for agent in self._agents.values():
            await agent.close()
        await self.comm_bus.clear()
        log.info("✅ Оркестратор закрыт")
