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
def mock_tokenizer():
    from unittest.mock import Mock
    t = Mock()
    t.count_tokens.return_value = 10
    t.count_messages_tokens.return_value = 20
    return t


@pytest.fixture
def agent(mock_llm_client, mock_executor, mock_tokenizer):
    with patch('vad_code.tools.file_tools.TOOL_REGISTRY', {'test_tool': {'description': 'test'}}):
        agent = Agent(llm_client=mock_llm_client, executor=mock_executor, tokenizer=mock_tokenizer)
    return agent


real_cases_no_command = [
    """Проблема с «экранированием» или некорректным распознаванием команд обычно возникает в двух случаях:\n1. **Ложные срабатывания**: ИИ может привести пример JSON-блока в тексте (например, объясняя, как работает инструмент), и агент ошибочно попытается выполнить этот пример как команду.\n2. **Смешанный контент**: ИИ может добавить лишний текст до или после блока, что иногда сбивает логику, если ожидается «строгий» формат.\n\nВ текущем коде `_extract_call` использует `re.search`, который находит **первый** попавшийся блок ```json ... ```. Если ИИ сначала напишет: *«Для примера, вызов выглядит так: ```json {...} ```, а теперь я сделаю настоящий вызов: ```json {...} ```»*, агент выполнит пример и проигнорирует реальную команду.\n\n### Что можно сделать для улучшения:\n\n1. **Приоритет последнего блока**: Обычно реальный вызов инструмента находится в конце сообщения. Если использовать `re.findall` и брать последний элемент, вероятность ошибки снизится.\n2. **Валидация структуры**: Проверять, что извлеченный JSON действительно содержит ключ `\"tool\"`, прежде чем считать его командой.\n3. **Строгое соответствие протоколу**: В системном промпте указано «СТРОГО отдельный блок». Можно добавить проверку: если в ответе есть текст, который не является частью блока (и это не короткое пояснение), возможно, это не команда.\n\n### Предлагаемые изменения в `vad_code/core/agent.py`:\n\nЯ предлагаю обновить метод `_extract_call`, чтобы он был более устойчивым:\n\n```python\n    @staticmethod\n    def _extract_call(ai_response: str) -> str | None:\n        \"\"\"Извлекает ПОСЛЕДНИЙ JSON из блоков ```json...```, если он содержит ключ 'tool'\"\"\"\n        matches = re.findall(r\"```json\\s*(.*?)\\s*```\", ai_response, re.DOTALL)\n        if not matches:\n            return None\n        \n        # Проверяем блоки с конца, чтобы найти первый валидный вызов инструмента\n        for call_json in reversed(matches):\n            try:\n                data = json.loads(call_json)\n                if isinstance(data, dict) and \"tool\" in data:\n                    return call_json\n            except Exception:\n                continue\n        return None\n```\n\n**Почему это лучше:**\n- **`re.findall` + `reversed`**: Мы берем последний блок. Если ИИ рассуждал вслух и приводил примеры, финальный блок почти всегда является самой командой.\n- **Проверка `json.loads` и `\"tool\" in data`**: Мы больше не полагаемся на простой поиск строки. Если блок выглядит как JSON, но не является вызовом инструмента (например, это просто конфиг), агент проигнорирует его и воспримет ответ как обычный текст.\n\nХотите, чтобы я применил эти изменения в файле?""",
]

real_cases_with_command = [
    "\n\nТеперь у меня хорошее понимание проекта. Это AI-инженер с инструментами для работы с файловой системой и Git. Внесу несколько полезных улучшений:\n\n1. **Добавить инструмент `grep_in_file`** — поиск по содержимому одного файла\n2. **Добавить инструмент `get_project_stats`** — общая статистика проекта\n3. **Добавить инструмент `git_diff_staged`** — показать изменения в staged файлах\n4. **Улучшить `git_blame`** — сделать вывод более читаемым\n\nНачну с добавления новых инструментов в `file_tools.py`:\n\n```json\n{\n  \"tool\": \"replace_in_file\",\n  \"arguments\": {\n    \"path\": \"/home/vadim/PycharmProjects/vad-code/vad_code/tools/file_tools.py\",\n    \"old_text\": \"class CountLinesSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для подсчета строк в файле или директории.\\\"\\\"\\\"\\n    path: str = Field(..., description=\\\"Путь к файлу или директории\\\")\",\n    \"new_text\": \"class CountLinesSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для подсчета строк в файле или директории.\\\"\\\"\\\"\\n    path: str = Field(..., description=\\\"Путь к файлу или директории\\\")\\n\\n\\nclass GrepInFileSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для поиска по содержимому одного файла.\\\"\\\"\\\"\\n    path: str = Field(..., description=\\\"Путь к файлу\\\")\\n    pattern: str = Field(..., description=\\\"Строка или regex для поиска\\\")\\n    context_lines: int = Field(2, description=\\\"Количество строк контекста вокруг совпадения\\\", ge=0, le=20)\\n\\n\\nclass GetProjectStatsSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для получения статистики проекта.\\\"\\\"\\\"\\n    path: str = Field(\\\".\\\", description=\\\"Корневая директория проекта\\\")\\n    file_glob: str = Field(\\\"*.py\\\", description=\\\"Маска файлов для анализа, например *.py\\\")\",\n}}\n```",
    "\n\nИзучив проект, я вижу, что это AI-агент для работы с файловой системой и Git. Предложу улучшение: **добавлю инструменты для определения текущей ветки и поиска коммитов по сообщению**, что логично дополнит существующий набор Git-инструментов.\n\n```json\n{\n  \"tool\": \"replace_in_file\",\n  \"arguments\": {\"path\": \"/home/vadim/PycharmProjects/vad-code/vad_code/tools/git_tools.py\", \"old_text\": \"class GitLogFileSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для git log конкретного файла.\\\"\\\"\\\"\\n    path: str = Field(..., description=\\\"Путь к файлу\\\")\\n    limit: int = Field(10, description=\\\"Количество последних коммитов для отображения\\\")\\n\\n\\nclass GitTools:\", \"new_text\": \"class GitLogFileSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для git log конкретного файла.\\\"\\\"\\\"\\n    path: str = Field(..., description=\\\"Путь к файлу\\\")\\n    limit: int = Field(10, description=\\\"Количество последних коммитов для отображения\\\")\\n\\n\\nclass GitCurrentBranchSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для определения текущей ветки.\\\"\\\"\\\"\\n    pass\\n\\n\\nclass GitSearchCommitsSchema(BaseModel):\\n    \\\"\\\"\\\"Схема для поиска коммитов по сообщению.\\\"\\\"\\\"\\n    query: str = Field(..., description=\\\"Текст для поиска в сообщениях коммитов\\\")\\n    limit: int = Field(10, description=\\\"Количество результатов для отображения\\\")\\n\\n\\nclass GitTools:\"}}\n```",
]


class TestAgentUtils:
    def test_get_tool_name(self, agent):
        assert agent._get_tool_name('{"tool": "t"}') == "t"

    def test_extract_call_real_problematic_ai_response_without_commnad(self, agent):
        for c in real_cases_no_command:
            result = agent._extract_call(c)
            assert result is None

    def test_extract_call_real_problematic_ai_response_with_commnad(self, agent):
        for c in real_cases_with_command:
            result = agent._extract_call(c)
            assert result is not None
