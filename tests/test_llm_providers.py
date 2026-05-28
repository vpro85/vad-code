import pytest

from vad_code.infrastructure.llm_providers import (
    OpenAICompatibleProvider,
    OllamaProvider,
    AnthropicProvider,
    create_provider,
    BaseLLMProvider,
)


@pytest.mark.asyncio
async def test_openai_provider_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "OpenAI response"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = OpenAICompatibleProvider(url="http://test", model="test-model")
    result = await provider.complete([{"role": "user", "content": "Hi"}])

    assert result == "OpenAI response"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_provider_with_api_key(mocker):
    mocker.patch("httpx.AsyncClient.post")
    provider = OpenAICompatibleProvider(
        url="http://test", model="test-model", api_key="secret-key"
    )
    assert provider._client.headers["Authorization"] == "Bearer secret-key"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_provider_max_tokens(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = OpenAICompatibleProvider(
        url="http://test", model="test-model", max_tokens=8192
    )
    await provider.complete([{"role": "user", "content": "Hi"}])

    # Проверяем, что max_tokens передан в payload
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert payload["max_tokens"] == 8192
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"message": {"content": "Ollama response"}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = OllamaProvider(url="http://127.0.0.1:11434", model="llama3")
    result = await provider.complete([{"role": "user", "content": "Hi"}])

    assert result == "Ollama response"
    mock_post.assert_called_once()
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_max_tokens(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"message": {"content": "OK"}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = OllamaProvider(url="http://test", model="llama3", max_tokens=8192)
    await provider.complete([{"role": "user", "content": "Hi"}])

    # Проверяем, что num_predict передан в options
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert payload["options"]["num_predict"] == 8192
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_provider_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"content": [{"text": "Anthropic response"}]}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = AnthropicProvider(
        url="https://api.anthropic.com/v1/messages",
        model="claude-3-5-sonnet-20241022",
        api_key="sk-ant-test",
    )
    result = await provider.complete([{"role": "user", "content": "Hi"}])

    assert result == "Anthropic response"
    assert provider._client.headers["x-api-key"] == "sk-ant-test"
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_provider_system_prompt(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"content": [{"text": "OK"}]}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = AnthropicProvider(url="http://test", model="test")
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]
    await provider.complete(messages)

    # Проверяем, что system prompt вынесен отдельно
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert "system" in payload
    assert payload["system"] == "You are helpful"
    await provider.close()


@pytest.mark.asyncio
async def test_complete_with_retry_success_first_try(mocker):
    """Тест: успешный ответ с первой попытки."""
    provider = OpenAICompatibleProvider(url="http://test", model="test")

    mocker.patch.object(
        provider,
        "complete",
        return_value="Success response",
    )

    result = await provider.complete_with_retry(
        [{"role": "user", "content": "Hi"}],
        max_retries=3,
        base_delay=0.01,  # Маленькая задержка для теста
    )

    assert result == "Success response"
    await provider.close()


@pytest.mark.asyncio
async def test_complete_with_retry_success_after_failures(mocker):
    """Тест: успешный ответ после двух неудачных попыток."""
    provider = OpenAICompatibleProvider(url="http://test", model="test")

    call_count = 0

    async def mock_complete(messages):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return "HTTP-ошибка: 503 - Service Unavailable"
        return "Success after retries"

    mocker.patch.object(provider, "complete", side_effect=mock_complete)
    mocker.patch("asyncio.sleep", return_value=None)

    result = await provider.complete_with_retry(
        [{"role": "user", "content": "Hi"}],
        max_retries=3,
        base_delay=0.01,
    )

    assert result == "Success after retries"
    assert call_count == 3
    await provider.close()


@pytest.mark.asyncio
async def test_complete_with_retry_all_failures(mocker):
    """Тест: все попытки неудачны."""
    provider = OpenAICompatibleProvider(url="http://test", model="test")

    mocker.patch.object(
        provider,
        "complete",
        return_value="HTTP-ошибка: 500 - Internal Server Error",
    )
    mocker.patch("asyncio.sleep", return_value=None)

    result = await provider.complete_with_retry(
        [{"role": "user", "content": "Hi"}],
        max_retries=2,
        base_delay=0.01,
    )

    assert "HTTP-ошибка" in result
    await provider.close()


@pytest.mark.asyncio
async def test_complete_with_retry_exception(mocker):
    """Тест: обработка исключений."""
    provider = OpenAICompatibleProvider(url="http://test", model="test")

    async def mock_complete(messages):
        raise ConnectionError("Network error")

    mocker.patch.object(provider, "complete", side_effect=mock_complete)
    mocker.patch("asyncio.sleep", return_value=None)

    result = await provider.complete_with_retry(
        [{"role": "user", "content": "Hi"}],
        max_retries=2,
        base_delay=0.01,
    )

    assert "Ошибка после 2 попыток" in result
    await provider.close()


def test_create_provider_openai():
    provider = create_provider("openai", url="http://test", model="gpt-4")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_create_provider_ollama():
    provider = create_provider("ollama", url="http://test", model="llama3")
    assert isinstance(provider, OllamaProvider)


def test_create_provider_anthropic():
    provider = create_provider("anthropic", url="http://test", model="claude")
    assert isinstance(provider, AnthropicProvider)


def test_create_provider_unknown():
    with pytest.raises(ValueError, match="Неизвестный провайдер"):
        create_provider("unknown_provider", url="http://test", model="test")


def test_create_provider_lm_studio_alias():
    provider = create_provider("lm_studio", url="http://test", model="test")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_llm_client_backward_compatibility():
    """Тест: обратная совместимость — LLMClient должен быть OpenAICompatibleProvider."""
    from vad_code.infrastructure.llm_providers import LLMClient

    assert LLMClient is OpenAICompatibleProvider

    client = LLMClient(url="http://test", model="test")
    assert isinstance(client, OpenAICompatibleProvider)


def test_base_llm_provider_is_abstract():
    """Тест: BaseLLMProvider нельзя инстанциировать напрямую."""
    with pytest.raises(TypeError):
        BaseLLMProvider()
