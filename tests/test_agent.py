import pytest
from unittest.mock import AsyncMock, MagicMock
from vad_code.core.agent import Agent
from vad_code.infrastructure.llm_client import LLMClient
from vad_code.core.executor import ToolExecutor
from vad_code.config import settings

@pytest.fixture
def mock_llm():
    client = MagicMock(spec=LLMClient)
    client.complete = AsyncMock()
    client.close = AsyncMock()
    return client

@pytest.fixture
def mock_executor():
    executor = MagicMock(spec=ToolExecutor)
    executor.execute = AsyncMock()
    return executor

@pytest.fixture
def agent(mock_llm, mock_executor):
    return Agent(llm_client=mock_llm, executor=mock_executor)

# PLACEHOLDER_UTILS