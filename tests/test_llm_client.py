import httpx
import pytest

from vad_code.infrastructure.llm_client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_complete_success(mocker):
    # Mock the AsyncClient.post method
    mock_post = mocker.patch("httpx.AsyncClient.post")

    # Setup mock response
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello world!"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    client = LLMClient()
    messages = [{"role": "user", "content": "Hi"}]
    result = await client.complete(messages)

    assert result == "Hello world!"
    mock_post.assert_called_once()
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_complete_http_error(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")

    # Setup mock to raise HTTPStatusError
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    error = httpx.HTTPStatusError(
        "Error",
        request=mocker.Mock(),
        response=mock_response
    )
    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = error

    client = LLMClient()
    result = await client.complete([{"role": "user", "content": "Hi"}])

    assert "HTTP-ошибка: 500" in result
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_complete_request_error(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection failed"))

    client = LLMClient()
    result = await client.complete([{"role": "user", "content": "Hi"}])

    assert "Ошибка соединения: Connection failed" in result
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_complete_format_error(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")

    # Return invalid JSON structure (missing 'choices')
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"wrong": "format"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    client = LLMClient()
    result = await client.complete([{"role": "user", "content": "Hi"}])

    assert "Ошибка: неожиданный формат ответа" in result
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_close(mocker):
    mock_aclose = mocker.patch("httpx.AsyncClient.aclose")
    client = LLMClient()
    await client.close()
    mock_aclose.assert_called_once()
