import pytest
import httpx
from vad_code.infrastructure.llm_providers import (
    OpenAICompatibleProvider,
    OllamaProvider,
    AnthropicProvider,
    create_provider,
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
async def test_ollama_provider_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "message": {"content": "Ollama response"}
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = OllamaProvider(url="http://127.0.0.1:11434", model="llama3")
    result = await provider.complete([{"role": "user", "content": "Hi"}])
    
    assert result == "Ollama response"
    mock_post.assert_called_once()
    await provider.close()


@pytest.mark.asyncio
async def test_anthropic_provider_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "content": [{"text": "Anthropic response"}]
    }
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
    mock_response.json.return_value = {
        "content": [{"text": "OK"}]
    }
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
