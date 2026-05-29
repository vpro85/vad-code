"""Тесты для мульти-агентной архитектуры."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vad_code.core.multi_agent.base_agent import AgentCapability, AgentType, BaseAgent
from vad_code.core.multi_agent.communication import (
    CommunicationBus,
    MessageType,
)
from vad_code.core.multi_agent.orchestrator import Orchestrator
from vad_code.core.multi_agent.agent_pool import AgentPool, WorkerConfig
from vad_code.core.multi_agent.specialized_agents import (
    CodeReviewAgent,
    TestingAgent,
    DocumentationAgent,
    SecurityAgent,
)


class MockAgent(BaseAgent):
    """Тестовый агент для unit-тестов."""

    def _setup_capabilities(self) -> None:
        self.capabilities = [
            AgentCapability(
                name="test_capability",
                description="Тестовая способность",
                priority=0.8,
                keywords=[
                    "test", "тест", "mock",
                    "review", "код", "code", "bug", "bugs",
                    "quality", "качество", "check", "проверка",
                ],
            ),
        ]

    def get_system_prompt(self) -> str:
        return "Ты - тестовый агент."

    async def handle_task(self, task: str, context: dict | None = None) -> str:
        return f"Выполнено: {task}"


@pytest.fixture
def mock_llm_client():
    """Создает мокированный LLM клиент."""
    client = AsyncMock()
    client.complete_with_retry = AsyncMock(return_value="Test response")
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_executor():
    """Создает мокированный executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value="File content")
    return executor


@pytest.fixture
def mock_tokenizer():
    """Создает мокированный токенизатор."""
    tokenizer = MagicMock()
    tokenizer.count_tokens = MagicMock(return_value=100)
    return tokenizer


# =============================================================================
# Тесты BaseAgent
# =============================================================================

class TestBaseAgent:
    """Тесты базового класса агента."""

    def test_agent_initialization(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет инициализацию агента."""
        agent = MockAgent(
            agent_type=AgentType.GENERAL,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Test prompt",
        )

        assert agent.agent_type == AgentType.GENERAL
        assert agent.system_prompt == "Test prompt"
        assert len(agent.capabilities) == 1
        assert agent.stats["tasks_completed"] == 0

    def test_can_handle_matching_task(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет оценку подходящей задачи."""
        agent = MockAgent(
            agent_type=AgentType.GENERAL,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Test prompt",
        )

        score = agent.can_handle("test task")
        assert score > 0

    def test_can_handle_non_matching_task(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет оценку неподходящей задачи."""
        agent = MockAgent(
            agent_type=AgentType.GENERAL,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Test prompt",
        )

        score = agent.can_handle("completely unrelated task xyz123")
        assert score == 0.0

    def test_get_info(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет получение информации об агенте."""
        agent = MockAgent(
            agent_type=AgentType.GENERAL,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Test prompt",
        )

        info = agent.get_info()
        assert info["type"] == "general"
        assert "capabilities" in info
        assert "stats" in info

    def test_repr(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет строковое представление."""
        agent = MockAgent(
            agent_type=AgentType.GENERAL,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Test prompt",
        )

        assert "MockAgent" in repr(agent)


# =============================================================================
# Тесты CommunicationBus
# =============================================================================

class TestCommunicationBus:
    """Тесты шины коммуникации."""

    def test_register_agent(self):
        """Проверяет регистрацию агента."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")

        assert "agent_1" in bus._queues

    def test_unregister_agent(self):
        """Проверяет удаление агента."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")
        bus.unregister_agent("agent_1")

        assert "agent_1" not in bus._queues

    @pytest.mark.asyncio
    async def test_send_point_to_point(self):
        """Проверяет точечную отправку."""
        bus = CommunicationBus()
        bus.register_agent("sender")
        bus.register_agent("receiver")

        message = await bus.send(
            message_type=MessageType.TASK,
            content="Test task",
            sender="sender",
            receiver="receiver",
        )

        assert message.message_type == MessageType.TASK
        assert message.content == "Test task"
        assert not bus._queues["receiver"].empty()

    @pytest.mark.asyncio
    async def test_send_broadcast(self):
        """Проверяет broadcast."""
        bus = CommunicationBus()
        bus.register_agent("sender")
        bus.register_agent("agent_1")
        bus.register_agent("agent_2")

        await bus.send(
            message_type=MessageType.BROADCAST,
            content="Broadcast message",
            sender="sender",
            receiver=None,
        )

        assert not bus._queues["agent_1"].empty()
        assert not bus._queues["agent_2"].empty()

    @pytest.mark.asyncio
    async def test_receive_message(self):
        """Проверяет получение сообщения."""
        bus = CommunicationBus()
        bus.register_agent("sender")
        bus.register_agent("receiver")

        await bus.send(
            message_type=MessageType.TASK,
            content="Test",
            sender="sender",
            receiver="receiver",
        )

        message = await bus.receive("receiver", timeout=1.0)
        assert message is not None
        assert message.content == "Test"

    @pytest.mark.asyncio
    async def test_receive_timeout(self):
        """Проверяет таймаут при получении."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")

        message = await bus.receive("agent_1", timeout=0.1)
        assert message is None

    @pytest.mark.asyncio
    async def test_get_history(self):
        """Проверяет получение истории."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")
        bus.register_agent("agent_2")

        # Отправляем сообщения
        await bus.send(MessageType.TASK, "Task 1", "agent_1", "agent_2")
        await bus.send(MessageType.RESULT, "Result 1", "agent_2", "agent_1")

        history = bus.get_history(limit=10)
        assert len(history) == 2

    def test_get_stats(self):
        """Проверяет статистику."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")
        bus.register_agent("agent_2")

        stats = bus.get_stats()
        assert stats["registered_agents"] == 2
        assert "by_type" in stats
        assert "queue_sizes" in stats

    @pytest.mark.asyncio
    async def test_clear(self):
        """Проверяет очистку."""
        bus = CommunicationBus()
        bus.register_agent("agent_1")

        await bus.send(MessageType.TASK, "Test", "orchestrator", "agent_1")
        await bus.clear()

        assert bus._queues["agent_1"].empty()
        assert len(bus._history) == 0


# =============================================================================
# Тесты Orchestrator
# =============================================================================

class TestOrchestrator:
    """Тесты оркестратора."""

    @pytest.fixture
    def orchestrator(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Создает оркестратор с тестовыми агентами."""
        orch = Orchestrator(mock_llm_client, mock_executor, mock_tokenizer)

        # Регистрируем тестовых агентов
        agent1 = MockAgent(
            agent_type=AgentType.CODE_REVIEW,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Code review agent",
        )
        orch.register_agent(agent1)

        return orch

    def test_register_agent(self, orchestrator):
        """Проверяет регистрацию агента."""
        agent = orchestrator.get_agent(AgentType.CODE_REVIEW)
        assert agent is not None

    def test_route_task(self, orchestrator):
        """Проверяет маршрутизацию задачи."""
        # Задача по code review должна идти к code review агенту
        agent_type = orchestrator.route_task("review this code for bugs")
        assert agent_type == AgentType.CODE_REVIEW

    def test_route_task_no_match(self, orchestrator):
        """Проверяет маршрутизацию при отсутствии подходящего агента."""
        # Задача без ключевых слов должна идти к общему агенту
        agent_type = orchestrator.route_task("xyz123 completely unrelated")
        assert agent_type == AgentType.GENERAL

    @pytest.mark.asyncio
    async def test_execute_task(self, orchestrator, mock_executor):
        """Проверяет выполнение задачи."""
        mock_executor.execute = AsyncMock(return_value="Test result")

        result = await orchestrator.execute_task("test task")

        assert result.success
        assert result.agent_type == AgentType.CODE_REVIEW
        assert orchestrator.stats["tasks_routed"] == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_context(self, orchestrator, mock_executor):
        """Проверяет выполнение задачи с контекстом."""
        mock_executor.execute = AsyncMock(return_value="File content")

        result = await orchestrator.execute_task(
            "test task",
            context={"file_path": "test.py"},
        )

        assert result.success

    def test_get_stats(self, orchestrator):
        """Проверяет статистику."""
        stats = orchestrator.get_stats()

        assert "orchestrator" in stats
        assert "agents" in stats
        assert "communication" in stats


# =============================================================================
# Тесты AgentPool
# =============================================================================

class TestAgentPool:
    """Тесты пула агентов."""

    @pytest.fixture
    def agent_pool(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Создает пул агентов."""
        agents = [
            MockAgent(
                agent_type=AgentType.CODE_REVIEW,
                llm_client=mock_llm_client,
                executor=mock_executor,
                tokenizer=mock_tokenizer,
                system_prompt="Agent 1",
            ),
            MockAgent(
                agent_type=AgentType.TESTING,
                llm_client=mock_llm_client,
                executor=mock_executor,
                tokenizer=mock_tokenizer,
                system_prompt="Agent 2",
            ),
        ]

        config = WorkerConfig(max_concurrent_tasks=2, task_timeout=10.0)
        return AgentPool(agents, config)

    def test_initialization(self, agent_pool):
        """Проверяет инициализацию пула."""
        assert len(agent_pool.agents) == 2
        assert agent_pool._config.max_concurrent_tasks == 2

    def test_submit_task(self, agent_pool):
        """Проверяет добавление задачи."""
        agent_pool.submit_task("test task")
        assert agent_pool.stats["tasks_submitted"] == 1

    @pytest.mark.asyncio
    async def test_process_next(self, agent_pool):
        """Проверяет обработку следующей задачи."""
        agent_pool.submit_task("test task")

        result = await agent_pool.process_next()
        assert result is not None
        assert result.success

    @pytest.mark.asyncio
    async def test_process_empty_queue(self, agent_pool):
        """Проверяет обработку пустой очереди."""
        result = await agent_pool.process_next()
        assert result is None

    def test_get_stats(self, agent_pool):
        """Проверяет статистику."""
        stats = agent_pool.get_stats()

        assert "queue_size" in stats
        assert "agents_count" in stats
        assert stats["agents_count"] == 2

    def test_clear_queue(self, agent_pool):
        """Проверяет очистку очереди."""
        agent_pool.submit_task("task 1")
        agent_pool.submit_task("task 2")
        agent_pool.clear_queue()

        assert agent_pool._task_queue.empty()


# =============================================================================
# Тесты специализированных агентов
# =============================================================================

class TestSpecializedAgents:
    """Тесты специализированных агентов."""

    def test_code_review_agent_capabilities(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет способности CodeReviewAgent."""
        agent = CodeReviewAgent(
            agent_type=AgentType.CODE_REVIEW,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Code review",
        )

        assert len(agent.capabilities) == 3
        assert agent.can_handle("review this code") > 0

    def test_testing_agent_capabilities(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет способности TestingAgent."""
        agent = TestingAgent(
            agent_type=AgentType.TESTING,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Testing",
        )

        assert len(agent.capabilities) == 3
        assert agent.can_handle("write tests for this") > 0

    def test_documentation_agent_capabilities(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет способности DocumentationAgent."""
        agent = DocumentationAgent(
            agent_type=AgentType.DOCUMENTATION,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Documentation",
        )

        assert len(agent.capabilities) == 3
        assert agent.can_handle("generate docstring") > 0

    def test_security_agent_capabilities(self, mock_llm_client, mock_executor, mock_tokenizer):
        """Проверяет способности SecurityAgent."""
        agent = SecurityAgent(
            agent_type=AgentType.SECURITY,
            llm_client=mock_llm_client,
            executor=mock_executor,
            tokenizer=mock_tokenizer,
            system_prompt="Security",
        )

        assert len(agent.capabilities) == 3
        assert agent.can_handle("security audit") > 0

    def test_agent_type_enum(self):
        """Проверяет enum типов агентов."""
        assert AgentType.CODE_REVIEW.value == "code_review"
        assert AgentType.TESTING.value == "testing"
        assert AgentType.DOCUMENTATION.value == "documentation"
        assert AgentType.SECURITY.value == "security"
        assert AgentType.GENERAL.value == "general"
