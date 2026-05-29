"""Тесты для оркестратора мульти-агентной системы."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from vad_code.core.multi_agent.base_agent import AgentType
from vad_code.core.multi_agent.orchestrator import Orchestrator, TaskResult
from vad_code.core.multi_agent.specialized_agents import (
    CodeReviewAgent,
    TestingAgent,
    DocumentationAgent,
    SecurityAgent,
)


@pytest.fixture
def mock_llm():
    """Создает мок LLM-провайдера."""
    llm = MagicMock()
    llm.complete_with_retry = AsyncMock(return_value="Ответ от LLM")
    return llm


@pytest.fixture
def mock_executor():
    """Создает мок исполнителя."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value="Содержимое файла")
    return executor


@pytest.fixture
def mock_tokenizer():
    """Создает мок токенизатора."""
    tokenizer = MagicMock()
    tokenizer.count_tokens.return_value = 100
    return tokenizer


@pytest.fixture
def orchestrator(mock_llm, mock_executor, mock_tokenizer):
    """Создает оркестратор с агентами."""
    orch = Orchestrator(mock_llm, mock_executor, mock_tokenizer)
    orch.create_default_agents()
    return orch


def test_orchestrator_init(orchestrator):
    """Тест: инициализация оркестратора."""
    assert orchestrator.stats["tasks_routed"] == 0
    assert orchestrator.stats["tasks_completed"] == 0
    assert orchestrator.stats["tasks_failed"] == 0


def test_create_default_agents(orchestrator):
    """Тест: создание стандартных агентов."""
    agents = orchestrator.get_all_agents()
    assert len(agents) == 4

    agent_types = {a.agent_type for a in agents}
    assert AgentType.CODE_REVIEW in agent_types
    assert AgentType.TESTING in agent_types
    assert AgentType.DOCUMENTATION in agent_types
    assert AgentType.SECURITY in agent_types


def test_route_task_code_review(orchestrator):
    """Тест: маршрутизация задачи на code review."""
    agent_type = orchestrator.route_task("проведи ревью кода")
    assert agent_type == AgentType.CODE_REVIEW


def test_route_task_testing(orchestrator):
    """Тест: маршрутизация задачи на тестирование."""
    agent_type = orchestrator.route_task("напиши тесты для функции")
    assert agent_type == AgentType.TESTING


def test_route_task_documentation(orchestrator):
    """Тест: маршрутизация задачи на документацию."""
    agent_type = orchestrator.route_task("добавь docstring к классу")
    assert agent_type == AgentType.DOCUMENTATION


def test_route_task_security(orchestrator):
    """Тест: маршрутизация задачи на аудит безопасности."""
    agent_type = orchestrator.route_task("проверь код на уязвимости")
    assert agent_type == AgentType.SECURITY


def test_route_task_general(orchestrator):
    """Тест: маршрутизация задачи на общего агента."""
    agent_type = orchestrator.route_task("привет, как дела?")
    assert agent_type == AgentType.GENERAL


def test_get_stats(orchestrator):
    """Тест: получение статистики."""
    stats = orchestrator.get_stats()
    assert "orchestrator" in stats
    assert "agents" in stats
    assert "communication" in stats
    assert len(stats["agents"]) == 4


@pytest.mark.asyncio
async def test_execute_task_success(orchestrator, mock_llm):
    """Тест: успешное выполнение задачи."""
    mock_llm.complete_with_retry = AsyncMock(return_value="Результат задачи")

    result = await orchestrator.execute_task("проверь код")

    assert result.success is True
    assert result.agent_type == AgentType.CODE_REVIEW
    assert orchestrator.stats["tasks_routed"] == 1
    assert orchestrator.stats["tasks_completed"] == 1


@pytest.mark.asyncio
async def test_execute_task_with_context(orchestrator, mock_llm, mock_executor):
    """Тест: выполнение задачи с контекстом."""
    mock_llm.complete_with_retry = AsyncMock(return_value="Результат")

    result = await orchestrator.execute_task(
        "проверь код",
        context={"file_path": "test.py"},
    )

    assert result.success is True
    mock_executor.execute.assert_called()


@pytest.mark.asyncio
async def test_execute_task_force_agent(orchestrator, mock_llm):
    """Тест: выполнение задачи с принудительным выбором агента."""
    mock_llm.complete_with_retry = AsyncMock(return_value="Результат")

    result = await orchestrator.execute_task(
        "привет",
        force_agent=AgentType.SECURITY,
    )

    assert result.success is True
    assert result.agent_type == AgentType.SECURITY


@pytest.mark.asyncio
async def test_execute_parallel(orchestrator, mock_llm):
    """Тест: параллельное выполнение задач."""
    mock_llm.complete_with_retry = AsyncMock(return_value="Результат")

    tasks = [
        ("проверь код", None),
        ("напиши тесты", None),
    ]

    results = await orchestrator.execute_parallel(tasks)

    assert len(results) == 2
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_execute_task_error(orchestrator, mock_llm):
    """Тест: обработка ошибки при выполнении задачи."""
    mock_llm.complete_with_retry = AsyncMock(side_effect=Exception("Ошибка LLM"))

    result = await orchestrator.execute_task(
        "проверь код",
        context={"file_content": "def foo(): pass"},
    )

    assert result.success is False
    assert result.error is not None
    assert orchestrator.stats["tasks_failed"] == 1


def test_agent_capabilities():
    """Тест: способности агентов настроены корректно."""
    mock_llm = MagicMock()
    mock_executor = MagicMock()
    mock_tokenizer = MagicMock()

    code_agent = CodeReviewAgent(
        agent_type=AgentType.CODE_REVIEW,
        llm_client=mock_llm,
        executor=mock_executor,
        tokenizer=mock_tokenizer,
        system_prompt="",
    )

    assert len(code_agent.capabilities) > 0
    assert code_agent.can_handle("проведи ревью кода") > 0
    assert code_agent.can_handle("привет") == 0

