import pytest
import json5
from pydantic import BaseModel, Field
from vad_code.core.executor import ToolExecutor

class ValidationSchema(BaseModel):
    param: str
    value: int = Field(gt=0)

@pytest.fixture
def executor():
    return ToolExecutor()

@pytest.mark.anyio
async def test_execute_invalid_json(executor):
    """Тест на передачу невалидного JSON."""
    result = await executor.execute("{ 'broken': json }")
    assert "Ошибка валидации" in result


@pytest.mark.anyio
async def test_execute_missing_tool_field(executor):
    """Тест на отсутствие поля 'tool' в JSON."""
    call_text = json5.dumps({"arguments": {"some": "data"}})
    result = await executor.execute(call_text)
    assert "Ошибка валидации" in result
    assert "Проверьте типы" in result

@pytest.mark.anyio
async def test_execute_validation_error(executor):
    """Тест на ошибку валидации аргументов через Pydantic."""
    async def dummy_tool(param: str, value: int):
        return "ok"
    
    executor.register_tool("test_tool", dummy_tool, schema=ValidationSchema)

    invalid_payload = json5.dumps({"tool": "test_tool", "arguments": {"param": "hello", "value": -1}})
    result = await executor.execute(invalid_payload)
    assert "Ошибка валидации аргументов" in result