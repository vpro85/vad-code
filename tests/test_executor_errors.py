import pytest
import json
from pydantic import BaseModel, Field
from vad_code.core.executor import ToolExecutor

class TestSchema(BaseModel):
    param: str
    value: int = Field(gt=0)

@pytest.fixture
def executor():
    return ToolExecutor()

@pytest.mark.asyncio
async def test_execute_invalid_json(executor):
    """Тест на передачу невалидного JSON."""
    result = await executor.execute("{ 'broken': json }")
    assert "Ошибка при выполнении инструмента" in result

@pytest.mark.asyncio
async def test_execute_missing_tool_field(executor):
    """Тест на отсутствие поля 'tool' в JSON."""
    call_text = json.dumps({"arguments": {"some": "data"}})
    result = await executor.execute(call_text)
    assert "Ошибка: В JSON не указано поле 'tool'." == result

@pytest.mark.asyncio
async def test_execute_validation_error(executor, TestSchema):
    """Тест на ошибку валидации аргументов через Pydantic."""
    async def dummy_tool(param: str, value: int):
        return "ok"
    
    executor.register_tool("test_tool", dummy_tool, schema=Test
    # Wait, I'll write the full clean version below to avoid mistakes.
