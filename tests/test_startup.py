"""Тесты запуска приложения — проверка, что всё загружается без ошибок."""

import pytest


def test_import_all_modules():
    """Проверяет, что все основные модули импортируются без ошибок."""
    # Core
    from vad_code.core.agent import Agent  # noqa: F401
    from vad_code.core.executor import ToolExecutor  # noqa: F401
    from vad_code.core.memory import ConversationMemory, SmartConversationMemory  # noqa: F401
    from vad_code.config import settings  # noqa: F401

    # Infrastructure
    from vad_code.infrastructure.llm_providers import (  # noqa: F401
        create_provider,
        OpenAICompatibleProvider,
        OllamaProvider,
        AnthropicProvider,
        BaseLLMProvider,
    )
    from vad_code.infrastructure.tokenizer import Tokenizer  # noqa: F401
    from vad_code.infrastructure.file_system import FileSystemService  # noqa: F401
    from vad_code.infrastructure.logger import log  # noqa: F401
    from vad_code.infrastructure.backup_manager import backup_manager  # noqa: F401
    from vad_code.infrastructure.audit_logger import audit_logger  # noqa: F401
    from vad_code.infrastructure.metrics import session_metrics  # noqa: F401

    # Tools
    from vad_code.tools.registry import TOOL_REGISTRY  # noqa: F401
    from vad_code.tools.permissions import permission_manager, ToolRiskLevel  # noqa: F401
    from vad_code.tools.schemas import ReadFileSchema, WriteFileSchema  # noqa: F401

    # Проверка, что настройки загружены
    assert settings.project_root is not None
    assert settings.llm_url is not None
    assert settings.llm_model is not None


def test_create_executor():
    """Проверяет, что ToolExecutor создаётся без ошибок."""
    from vad_code.core.executor import ToolExecutor

    executor = ToolExecutor()
    assert executor.tools == {}
    assert executor.timeout == 120  # DEFAULT_TIMEOUT


def test_create_tokenizer():
    """Проверяет, что Tokenizer создаётся без ошибок."""
    from vad_code.infrastructure.tokenizer import Tokenizer

    tokenizer = Tokenizer()
    assert tokenizer is not None
    # Проверка, что токенизатор работает
    tokens = tokenizer.count_tokens("test message")
    assert tokens > 0


def test_create_file_system_service():
    """Проверяет, что FileSystemService создаётся без ошибок."""
    from vad_code.infrastructure.file_system import FileSystemService

    service = FileSystemService()
    assert service.root is not None


def test_create_llm_provider():
    """Проверяет, что LLM-провайдер создаётся без ошибок."""
    from vad_code.infrastructure.llm_providers import create_provider

    provider = create_provider(
        provider_type="openai",
        url="http://127.0.0.1:1234/v1/chat/completions",
        model="test-model",
    )
    assert provider is not None
    # Закрываем провайдера
    import asyncio
    asyncio.run(provider.close())


def test_create_memory():
    """Проверяет, что ConversationMemory создаётся без ошибок."""
    from vad_code.core.memory import ConversationMemory
    from vad_code.infrastructure.tokenizer import Tokenizer

    tokenizer = Tokenizer()
    memory = ConversationMemory(tokenizer, "Test system prompt")
    assert memory.history == []
    assert memory.system_prompt == "Test system prompt"


def test_tool_registry_not_empty():
    """Проверяет, что реестр инструментов не пуст."""
    from vad_code.tools.registry import TOOL_REGISTRY

    assert len(TOOL_REGISTRY) > 0
    # Проверка структуры записи
    for name, info in TOOL_REGISTRY.items():
        assert "description" in info
        assert "risk_level" in info


def test_permission_manager_initialized():
    """Проверяет, что менеджер разрешений инициализирован."""
    from vad_code.tools.permissions import permission_manager

    assert permission_manager is not None


def test_backup_manager_initialized():
    """Проверяет, что менеджер бэкапов инициализирован."""
    from vad_code.infrastructure.backup_manager import backup_manager

    assert backup_manager is not None


def test_audit_logger_initialized():
    """Проверяет, что аудит-логгер инициализирован."""
    from vad_code.infrastructure.audit_logger import audit_logger

    assert audit_logger is not None


def test_session_metrics_initialized():
    """Проверяет, что метрики сессии инициализированы."""
    from vad_code.infrastructure.metrics import session_metrics

    assert session_metrics is not None


def test_settings_defaults():
    """Проверяет, что настройки имеют допустимые значения."""
    from vad_code.config import settings

    # Значения могут переопределяться через .env, проверяем только типы и диапазоны
    assert isinstance(settings.max_iterations, int)
    assert settings.max_iterations > 0
    assert isinstance(settings.max_history_messages, int)
    assert settings.max_history_messages > 0
    assert isinstance(settings.timeout, int)
    assert settings.timeout > 0
    assert isinstance(settings.max_context_tokens, int)
    assert settings.max_context_tokens > 0
    assert isinstance(settings.enable_multi_agent, bool)


def test_agent_creation_with_mocks():
    """Проверяет, что Agent создаётся с моковыми зависимостями."""
    from unittest.mock import MagicMock, AsyncMock
    from vad_code.core.agent import Agent
    from vad_code.core.executor import ToolExecutor
    from vad_code.infrastructure.tokenizer import Tokenizer

    # Моки
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock()
    mock_llm.close = AsyncMock()

    executor = ToolExecutor()
    tokenizer = Tokenizer()

    agent = Agent(llm_client=mock_llm, executor=executor, tokenizer=tokenizer)
    assert agent is not None
    assert agent.system_prompt is not None


@pytest.mark.asyncio
async def test_agent_close():
    """Проверяет, что agent.close() выполняется без ошибок."""
    from unittest.mock import MagicMock, AsyncMock
    from vad_code.core.agent import Agent
    from vad_code.core.executor import ToolExecutor
    from vad_code.infrastructure.tokenizer import Tokenizer

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock()
    mock_llm.close = AsyncMock()

    executor = ToolExecutor()
    tokenizer = Tokenizer()

    agent = Agent(llm_client=mock_llm, executor=executor, tokenizer=tokenizer)
    await agent.close()

    # Проверка, что close был вызван у LLM
    mock_llm.close.assert_called_once()


def test_file_tools_creation():
    """Проверяет, что FileTools создаётся без ошибок."""
    from vad_code.tools import FileTools

    file_tools = FileTools()
    assert file_tools is not None
    # Проверка, что основные методы существуют
    assert hasattr(file_tools, "read_file")
    assert hasattr(file_tools, "write_file")
    assert hasattr(file_tools, "list_files")


def test_git_tools_creation():
    """Проверяет, что GitTools создаётся без ошибок."""
    from vad_code.tools.git_tools import GitTools

    git_tools = GitTools()
    assert git_tools is not None
    assert hasattr(git_tools, "git_status")
    assert hasattr(git_tools, "git_diff")


def test_schemas_validation():
    """Проверяет, что Pydantic-схемы валидируют данные."""
    from vad_code.tools.schemas import ReadFileSchema, WriteFileSchema

    # Валидная схема
    schema = ReadFileSchema(path="test.txt")
    assert schema.path == "test.txt"

    # Неверная схема должна вызвать ошибку
    with pytest.raises(Exception):
        WriteFileSchema(path="test.txt")  # content обязателен


def test_risk_levels_defined():
    """Проверяет, что уровни риска определены."""
    from vad_code.tools.permissions import ToolRiskLevel

    assert hasattr(ToolRiskLevel, "READ")
    assert hasattr(ToolRiskLevel, "WRITE")
    assert hasattr(ToolRiskLevel, "DANGEROUS")


def test_memory_backward_compatibility():
    """Проверяет обратную совместимость алиаса ConversationMemory."""
    from vad_code.core.memory import ConversationMemory, SmartConversationMemory

    assert ConversationMemory is SmartConversationMemory


def test_llm_client_backward_compatibility():
    """Проверяет обратную совместимость LLMClient."""
    from vad_code.infrastructure.llm_providers import (
        LLMClient,
        OpenAICompatibleProvider,
    )

    assert LLMClient is OpenAICompatibleProvider
