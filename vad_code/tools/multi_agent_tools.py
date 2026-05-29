"""Инструменты для управления мульти-агентной системой."""

from typing import Any

from vad_code.core.multi_agent.base_agent import AgentType
from vad_code.core.multi_agent.orchestrator import Orchestrator
from vad_code.infrastructure.logger import log
from vad_code.tools.permissions import register_tool, ToolRiskLevel
from vad_code.tools.schemas import (
    ListAgentsSchema,
    GetOrchestratorStatsSchema,
    RouteTaskSchema,
    ExecuteWithAgentSchema,
    ExecuteParallelTasksSchema,
    GetCommunicationHistorySchema,
    ResetAgentsSchema,
)


class MultiAgentTools:
    """Инструменты для взаимодействия с мульти-агентной системой."""

    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        """
        Инициализация инструментов.

        :param orchestrator: Оркестратор мульти-агентной системы
        """
        self._orchestrator = orchestrator

    @property
    def orchestrator(self) -> Orchestrator:
        """Получает оркестратор."""
        if self._orchestrator is None:
            raise RuntimeError("Оркестратор не инициализирован")
        return self._orchestrator

    @orchestrator.setter
    def orchestrator(self, value: Orchestrator | None) -> None:
        """Устанавливает оркестратор."""
        self._orchestrator = value

    @register_tool(
        description="Возвращает список всех зарегистрированных агентов и их возможности.",
        schema=ListAgentsSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def list_agents(self) -> str:
        """Возвращает список всех зарегистрированных агентов."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен. Включите его через /multi-agent."

        agents = self._orchestrator.get_all_agents()
        if not agents:
            return "Нет зарегистрированных агентов."

        result = "🤖 Зарегистрированные агенты:\n\n"
        for agent in agents:
            info = agent.get_info()
            result += f"## {agent.__class__.__name__}\n"
            result += f"- **Тип:** `{info['type']}`\n"
            result += "- **Способности:**\n"
            for cap in info.get("capabilities", []):
                result += f"  - {cap['name']}: {cap['description']}\n"
            stats = info.get("stats", {})
            result += f"- **Статистика:** {stats.get('tasks_completed', 0)} задач, "
            result += f"{stats.get('errors', 0)} ошибок\n\n"

        return result

    @register_tool(
        description="Возвращает статистику оркестратора и агентов.",
        schema=GetOrchestratorStatsSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def get_orchestrator_stats(self) -> str:
        """Возвращает статистику оркестратора."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        stats = self._orchestrator.get_stats()
        orch_stats = stats.get("orchestrator", {})

        result = "📊 Статистика оркестратора:\n\n"
        result += f"- **Задач маршрутизировано:** {orch_stats.get('tasks_routed', 0)}\n"
        result += f"- **Задач выполнено:** {orch_stats.get('tasks_completed', 0)}\n"
        result += f"- **Задач провалено:** {orch_stats.get('tasks_failed', 0)}\n"
        result += f"- **Среднее время выполнения:** {orch_stats.get('avg_execution_time_ms', 0):.0f}ms\n\n"

        agents_stats = stats.get("agents", {})
        if agents_stats:
            result += "### Статистика агентов:\n\n"
            for agent_type, agent_info in agents_stats.items():
                result += f"**{agent_type}:**\n"
                agent_stats = agent_info.get("stats", {})
                result += f"- Выполнено: {agent_stats.get('tasks_completed', 0)}\n"
                result += f"- Ошибок: {agent_stats.get('errors', 0)}\n\n"

        return result

    @register_tool(
        description="Определяет, какой агент лучше всего подходит для задачи.",
        schema=RouteTaskSchema,
        risk_level=ToolRiskLevel.READ,
    )
    async def route_task(self, task: str) -> str:
        """Определяет, какой агент лучше всего подходит для задачи."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        agent_type = self._orchestrator.route_task(task)
        agent = self._orchestrator.get_agent(agent_type)

        if agent:
            return f"📍 Задача маршрутизирована на **{agent.__class__.__name__}** (`{agent_type.value}`)"
        return f"📍 Задача маршрутизирована на агента типа `{agent_type.value}`"

    @register_tool(
        description="Выполняет задачу через подходящего агента (автовыбор или конкретный тип).",
        schema=ExecuteWithAgentSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    async def execute_with_agent(
        self,
        task: str,
        agent_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Выполняет задачу через подходящего агента."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        force_agent = None
        if agent_type:
            try:
                force_agent = AgentType(agent_type.lower())
            except ValueError:
                return (
                    f"❌ Неизвестный тип агента: `{agent_type}`. "
                    "Доступные: code_review, testing, documentation, security, general"
                )

        result = await self._orchestrator.execute_task(
            task, context=context, force_agent=force_agent
        )

        if result.success:
            return (
                f"✅ Задача выполнена агентом `{result.agent_type.value}` "
                f"за {result.execution_time_ms:.0f}ms\n\n{result.result}"
            )
        else:
            return f"❌ Ошибка выполнения задачи агентом `{result.agent_type.value}`: {result.error}"

    @register_tool(
        description="Выполняет несколько задач параллельно через разных агентов.",
        schema=ExecuteParallelTasksSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    async def execute_parallel_tasks(
        self,
        tasks: list[str],
        contexts: list[dict[str, Any] | None] | None = None,
    ) -> str:
        """Выполняет несколько задач параллельно."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        if not tasks:
            return "Список задач пуст."

        if contexts is None:
            contexts = [None] * len(tasks)

        # Проверка соответствия количества задач и контекстов
        if len(contexts) != len(tasks):
            log.warning(
                "Количество контекстов (%d) не совпадает с количеством задач (%d). "
                "Добавляем пустые контексты.",
                len(contexts),
                len(tasks),
            )
            contexts = list(contexts) + [None] * (len(tasks) - len(contexts))

        task_tuples = list(zip(tasks, contexts))
        results = await self._orchestrator.execute_parallel(task_tuples)

        result = f"🚀 Выполнено {len(results)} задач:\n\n"
        for i, r in enumerate(results, 1):
            status = "✅" if r.success else "❌"
            result += f"{status} **Задача {i}** (агент: `{r.agent_type.value}`, "
            result += f"время: {r.execution_time_ms:.0f}ms)\n"
            if r.success:
                result += f"Результат: {r.result[:200]}\n\n"
            else:
                result += f"Ошибка: {r.error}\n\n"

        return result

    @register_tool(
        description="Возвращает историю сообщений между агентами.",
        schema=GetCommunicationHistorySchema,
        risk_level=ToolRiskLevel.READ,
    )
    def get_communication_history(self) -> str:
        """Возвращает историю сообщений между агентами."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        history = self._orchestrator.comm_bus.get_history()
        if not history:
            return "История сообщений пуста."

        result = "📨 История сообщений:\n\n"
        for msg in history[-20:]:  # Последние 20 сообщений
            result += f"- [{msg.message_type.value}] {msg.sender} -> {msg.receiver}: "
            result += f"{msg.content[:100]}\n"

        return result

    @register_tool(
        description="Сбрасывает статистику всех агентов.",
        schema=ResetAgentsSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def reset_agents(self) -> str:
        """Сбрасывает статистику всех агентов."""
        if self._orchestrator is None:
            return "Мульти-агентный режим не активен."

        agents = self._orchestrator.get_all_agents()
        for agent in agents:
            agent.stats = {
                "tasks_completed": 0,
                "errors": 0,
                "total_tokens": 0,
                "avg_response_time_ms": 0,
            }

        self._orchestrator.stats = {
            "tasks_routed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time_ms": 0,
        }

        return f"🧹 Статистика сброшена для {len(agents)} агентов."
