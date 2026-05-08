from unittest.mock import AsyncMock, patch

import pytest

from vad_code.core.agent import Agent


@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.complete = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def agent(mock_llm_client, mock_executor):
    with patch('vad_code.tools.file_tools.TOOL_REGISTRY', {'test_tool': {'description': 'test'}}):
        agent = Agent(llm_client=mock_llm_client, executor=mock_executor)
    return agent


REAL_CASE_STR = """Проблема с «экранированием» или некорректным распознаванием команд обычно возникает в двух случаях:\n1. **Ложные срабатывания**: ИИ может привести пример JSON-блока в тексте (например, объясняя, как работает инструмент), и агент ошибочно попытается выполнить этот пример как команду.\n2. **Смешанный контент**: ИИ может добавить лишний текст до или после блока, что иногда сбивает логику, если ожидается «строгий» формат.\n\nВ текущем коде `_extract_call` использует `re.search`, который находит **первый** попавшийся блок ```json ... ```. Если ИИ сначала напишет: *«Для примера, вызов выглядит так: ```json {...} ```, а теперь я сделаю настоящий вызов: ```json {...} ```»*, агент выполнит пример и проигнорирует реальную команду.\n\n### Что можно сделать для улучшения:\n\n1. **Приоритет последнего блока**: Обычно реальный вызов инструмента находится в конце сообщения. Если использовать `re.findall` и брать последний элемент, вероятность ошибки снизится.\n2. **Валидация структуры**: Проверять, что извлеченный JSON действительно содержит ключ `\"tool\"`, прежде чем считать его командой.\n3. **Строгое соответствие протоколу**: В системном промпте указано «СТРОГО отдельный блок». Можно добавить проверку: если в ответе есть текст, который не является частью блока (и это не короткое пояснение), возможно, это не команда.\n\n### Предлагаемые изменения в `vad_code/core/agent.py`:\n\nЯ предлагаю обновить метод `_extract_call`, чтобы он был более устойчивым:\n\n```python\n    @staticmethod\n    def _extract_call(ai_response: str) -> str | None:\n        \"\"\"Извлекает ПОСЛЕДНИЙ JSON из блоков ```json...```, если он содержит ключ 'tool'\"\"\"\n        matches = re.findall(r\"```json\\s*(.*?)\\s*```\", ai_response, re.DOTALL)\n        if not matches:\n            return None\n        \n        # Проверяем блоки с конца, чтобы найти первый валидный вызов инструмента\n        for call_json in reversed(matches):\n            try:\n                data = json.loads(call_json)\n                if isinstance(data, dict) and \"tool\" in data:\n                    return call_json\n            except Exception:\n                continue\n        return None\n```\n\n**Почему это лучше:**\n- **`re.findall` + `reversed`**: Мы берем последний блок. Если ИИ рассуждал вслух и приводил примеры, финальный блок почти всегда является самой командой.\n- **Проверка `json.loads` и `\"tool\" in data`**: Мы больше не полагаемся на простой поиск строки. Если блок выглядит как JSON, но не является вызовом инструмента (например, это просто конфиг), агент проигнорирует его и воспримет ответ как обычный текст.\n\nХотите, чтобы я применил эти изменения в файле?"""


class TestAgentUtils:
    def test_get_tool_name(self, agent):
        assert agent._get_tool_name('{"tool": "t"}') == "t"

    def test_extract_call_real_problematic_ai_response(self, agent):
        result = agent._extract_call(REAL_CASE_STR)
        assert result is None
