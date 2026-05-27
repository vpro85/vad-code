"""Тесты для ToolExecutor — покрытие основных путей выполнения."""
import pytest
import json5
from unittest.mock import AsyncMock, MagicMock
from vad_code.core.executor import ToolExecutor


@pytest.fixture
def executor():
    return ToolExecutor()


@pytest.mark.anyio
async def test_execute_sync_tool(executor):
    """Тест выполнения синхронного инструмента."""

    def sync_tool(x: int, y: int) -> int:
        return x + y

    executor.register_tool("add", sync_tool)
    call_text = json5.dumps({"tool": "add", "arguments": {"x": 3, "y": 4}})
    result = await executor.execute(call_text)
    assert result == "7"


@pytest.mark.anyio
async def test_execute_async_tool(executor):
    """Тест выполнения асинхронного инструмента."""

    async def async_tool(name: str) -> str:
        return f"Hello, {name}!"

    executor.register_tool("greet", async_tool)
    call_text = json5.dumps({"tool": "greet", "arguments": {"name": "World"}})
    result = await executor.execute(call_text)
    assert result == "Hello, World!"


@pytest.mark.anyio
async def test_execute_tool_returns_none(executor):
    """Тест инструмента, возвращающего None."""

    def no_return_tool():
        pass

    executor.register_tool("no_return", no_return_tool)
    call_text = json5.dumps({"tool": "no_return", "arguments": {}})
    result = await executor.execute(call_text)
    assert result == "Success"


@pytest.mark.anyio
async def test_execute_tool_not_found(executor):
    """Тест вызова незарегистрированного инструмента."""
    call_text = json5.dumps({"tool": "nonexistent", "arguments": {}})
    result = await executor.execute(call_text)
    assert "не зарегистрирован" in result


@pytest.mark.anyio
async def test_execute_tool_raises_os_error(executor):
    """Тест обработки OSError при выполнении инструмента."""

    def failing_tool():
        raise OSError("Disk full")

    executor.register_tool("failing", failing_tool)
    call_text = json5.dumps({"tool": "failing", "arguments": {}})
    result = await executor.execute(call_text)
    assert "Ошибка при выполнении инструмента" in result


@pytest.mark.anyio
async def test_execute_tool_raises_type_error(executor):
    """Тест обработки TypeError при выполнении инструмента."""

    def type_error_tool(x):
        return x + "string"

    executor.register_tool("type_error", type_error_tool)
    call_text = json5.dumps({"tool": "type_error", "arguments": {"x": 123}})
    result = await executor.execute(call_text)
    assert "Ошибка при выполнении инструмента" in result


@pytest.mark.anyio
async def test_execute_with_schema_validation_success(executor):
    """Тест успешной валидации через Pydantic-схему."""
    from pydantic import BaseModel, Field
    class MySchema(BaseModel):
        name: str
        age: int = Field(ge=0)

    def my_tool(name: str, age: int) -> str:
        return f"{name} is {age} years old"

    executor.register_tool("my_tool", my_tool, schema=MySchema)
    call_text = json5.dumps({"tool": "my_tool", "arguments": {"name": "Alice", "age": 30}})
    result = await executor.execute(call_text)
    assert result == "Alice is 30 years old"


@pytest.mark.anyio
async def test_execute_with_schema_validation_failure(executor):
    """Тест ошибки валидации через Pydantic-схему."""
    from pydantic import BaseModel, Field
    class MySchema(BaseModel):
        name: str
        age: int = Field(ge=0)

    def my_tool(name: str, age: int) -> str:
        return f"{name} is {age} years old"

    executor.register_tool("my_tool", my_tool, schema=MySchema)
    call_text = json5.dumps({"tool": "my_tool", "arguments": {"name": "Alice", "age": -5}})
    result = await executor.execute(call_text)
    assert "Ошибка валидации аргументов" in result


@pytest.mark.anyio
async def test_execute_empty_tool_name(executor):
    """Тест с пустым именем инструмента."""
    call_text = json5.dumps({"tool": "", "arguments": {}})
    result = await executor.execute(call_text)
    assert "Ошибка: В JSON не указано поле 'tool'." == result


@pytest.mark.anyio
async def test_execute_tool_with_no_arguments_key(executor):
    """Тест вызова инструмента без ключа arguments."""

    def no_args_tool():
        return "ok"

    executor.register_tool("no_args", no_args_tool)
    call_text = json5.dumps({"tool": "no_args"})
    result = await executor.execute(call_text)
    assert result == "ok"
