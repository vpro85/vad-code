"""Тесты для мульти-агентных инструментов."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vad_code.core.multi_agent.base_agent import AgentType
from vad_code.core.multi_agent.orchestrator import Orchestrator, TaskResult
from vad_code.tools.multi_agent_tools import MultiAgentTools


@pytest.fixture
def mock_orchestrator():
    """Создает мок оркестратора."""
    orch = MagicMock(spec=Orchestrator)
    orch.get_all_agents.return_value = []
    orch.get_stats.return_value = {
        "orchestrator": {
            "tasks_routed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_execution_time_ms": 0,
        },
        "agents": {},
        "communication": {"total_messages": 0},
    }
    orch.route_task.return_value = AgentType.GENERAL
    orch.get_agent.return_value = None
    orch.execute_task = AsyncMock(return_value=TaskResult(
        agent_type=AgentType.GENERAL,
        success=True,
        result="Задача выполнена",
        execution_time_ms=100,
    ))
    orch.execute_parallel = AsyncMock(return_value=[
        TaskResult(
            agent_type=AgentType.CODE_REVIEW,
            success=True,
            result="Code review выполнен",
            execution_time_ms=200,
        ),
        TaskResult(
            agent_type=AgentType.TESTING,
            success=True,
            result="Тесты написаны",
            execution_time_ms=150,
        ),
    ])
    orch.comm_bus = MagicMock()
    orch.comm_bus.get_history.return_value = []
    orch.stats = {"tasks_routed": 0, "tasks_completed": 0, "tasks_failed": 0, "total_execution_time_ms": 0}
    return orch


@pytest.fixture
def multi_agent_tools(mock_orchestrator):
    """Создает инструменты с оркестратором."""
    tools = MultiAgentTools(orchestrator=mock_orchestrator)
    return tools


@pytest.fixture
def multi_agent_tools_no_orch():
    """Создает инструменты без оркестратора."""
    return MultiAgentTools()


def test_list_agents_empty(multi_agent_tools, mock_orchestrator):
    """Тест: список агентов пуст."""
    mock_orchestrator.get_all_agents.return_value = []
    result = multi_agent_tools.list_agents()
    assert "Нет зарегистрированных агентов" in result


def test_list_agents_with_agents(multi_agent_tools, mock_orchestrator):
    """Тест: список агентов с агентами."""
    mock_agent = MagicMock()
    mock_agent.__class__.__name__ = "CodeReviewAgent"
    mock_agent.get_info.return_value = {
        "type": "code_review",
        "capabilities": [
            {"name": "review", "description": "Code review"}
        ],
        "stats": {"tasks_completed": 5, "errors": 0},
    }
    mock_orchestrator.get_all_agents.return_value = [mock_agent]

    result = multi_agent_tools.list_agents()
    assert "CodeReviewAgent" in result
    assert "code_review" in result
    assert "5 задач" in result


def test_list_agents_disabled(multi_agent_tools_no_orch):
    """Тест: агенты недоступны без оркестратора."""
    result = multi_agent_tools_no_orch.list_agents()
    assert "Мульти-агентный режим не активен" in result


def test_get_orchestrator_stats(multi_agent_tools, mock_orchestrator):
    """Тест: статистика оркестратора."""
    mock_orchestrator.get_stats.return_value = {
        "orchestrator": {
            "tasks_routed": 10,
            "tasks_completed": 8,
            "tasks_failed": 2,
            "avg_execution_time_ms": 150.5,
        },
        "agents": {
            "code_review": {"stats": {"tasks_completed": 5}},
        },
        "communication": {"total_messages": 20},
    }

    result = multi_agent_tools.get_orchestrator_stats()
    assert "10" in result
    assert "8" in result
    assert "2" in result
    assert "150ms" in result


@pytest.mark.asyncio
async def test_route_task(multi_agent_tools, mock_orchestrator):
    """Тест: маршрутизация задачи."""
    mock_orchestrator.route_task.return_value = AgentType.CODE_REVIEW
    mock_agent = MagicMock()
    mock_agent.__class__.__name__ = "CodeReviewAgent"
    mock_orchestrator.get_agent.return_value = mock_agent

    result = await multi_agent_tools.route_task("проверь код на ошибки")
    assert "CodeReviewAgent" in result
    assert "code_review" in result


@pytest.mark.asyncio
async def test_execute_with_agent(multi_agent_tools, mock_orchestrator):
    """Тест: выполнение задачи через агента."""
    result = await multi_agent_tools.execute_with_agent("напиши тесты")
    assert "general" in result.lower() or "Задача выполнена" in result


@pytest.mark.asyncio
async def test_execute_with_agent_specific(multi_agent_tools, mock_orchestrator):
    """Тест: выполнение задачи через конкретного агента."""
    mock_orchestrator.execute_task = AsyncMock(return_value=TaskResult(
        agent_type=AgentType.TESTING,
        success=True,
        result="Тесты написаны",
        execution_time_ms=100,
    ))

    result = await multi_agent_tools.execute_with_agent(
        "напиши тесты",
        agent_type="testing",
    )
    assert "testing" in result.lower() or "Тесты написаны" in result


@pytest.mark.asyncio
async def test_execute_with_agent_invalid_type(multi_agent_tools, mock_orchestrator):
    """Тест: выполнение задачи с неверным типом агента."""
    result = await multi_agent_tools.execute_with_agent(
        "задача",
        agent_type="nonexistent",
    )
    assert "Неизвестный тип агента" in result


@pytest.mark.asyncio
async def test_execute_parallel_tasks(multi_agent_tools, mock_orchestrator):
    """Тест: параллельное выполнение задач."""
    result = await multi_agent_tools.execute_parallel_tasks([
        "проверь код",
        "напиши тесты",
    ])
    assert "2 задач" in result
    assert "CodeReviewAgent" in result or "code_review" in result


@pytest.mark.asyncio
async def test_execute_parallel_tasks_empty(multi_agent_tools, mock_orchestrator):
    """Тест: параллельное выполнение пустого списка."""
    result = await multi_agent_tools.execute_parallel_tasks([])
    assert "Список задач пуст" in result


def test_get_communication_history(multi_agent_tools, mock_orchestrator):
    """Тест: история сообщений."""
    result = multi_agent_tools.get_communication_history()
    assert "История сообщений пуста" in result


def test_reset_agents(multi_agent_tools, mock_orchestrator):
    """Тест: сброс статистики агентов."""
    mock_agent = MagicMock()
    mock_orchestrator.get_all_agents.return_value = [mock_agent]

    result = multi_agent_tools.reset_agents()
    assert "Статистика сброшена" in result
    assert "1 агентов" in result


def test_orchestrator_property_raises_when_none(multi_agent_tools_no_orch):
    """Тест: свойство orchestrator выбрасывает ошибку, если не инициализирован."""
    with pytest.raises(RuntimeError, match="Оркестратор не инициализирован"):
        _ = multi_agent_tools_no_orch.orchestrator

