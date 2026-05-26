from unittest.mock import AsyncMock, MagicMock

import pytest

from vad_code.core.agent import Agent
from vad_code.core.executor import ToolExecutor
from vad_code.infrastructure.llm_client import LLMClient


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
class TestExtractCall:
    def test_extract_json_block(self):
        response = """Here is the tool call:
```json
{
  "tool": "read_file",
  "arguments": {"path": "test.txt"}
}
```
Done."""
        result = Agent._extract_call(response)
        assert result is not None
        assert "read_file" in result

    def test_extract_plain_json(self):
        response = """I will read the file.
{
  "tool": "write_file",
  "arguments": {"path": "test.txt", "content": "hello"}
}
Let me know if it worked."""
        result = Agent._extract_call(response)
        assert result is not None
        assert "write_file" in result

    def test_extract_no_tool_key(self):
        response = """{
  "some_key": "value"
}"""
        result = Agent._extract_call(response)
        assert result is None

    def test_extract_invalid_json(self):
        response = """{
  tool: read_file
}"""
        result = Agent._extract_call(response)
        assert result is None

    def test_extract_last_valid_json(self):
        response = """First attempt:
```json
{
  "tool": "list_files"
}
```
Second attempt:
```json
{
  "tool": "read_file",
  "arguments": {"path": "test.txt"}
}
```
"""
        result = Agent._extract_call(response)
        assert result is not None
        assert "read_file" in result

    def test_extract_no_json(self):
        response = "I don't need any tools."
        result = Agent._extract_call(response)
        assert result is None

    def test_extract_json_with_backticks_in_content(self):
        response = """Here is the code:
```json
{
  "tool": "write_file",
  "arguments": {
    "path": "test.py",
    "content": "def hello():\n    print('```')"
  }
}
```
Done."""
        result = Agent._extract_call(response)
        assert result is not None
        assert "write_file" in result
