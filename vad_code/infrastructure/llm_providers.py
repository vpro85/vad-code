"""
Абстракция LLM-провайдеров.
Поддерживает OpenAI-compatible (LM Studio, OpenAI), Ollama, Anthropic.
"""
import abc
import asyncio
from typing import Any

import httpx

from vad_code.infrastructure.logger import log


class BaseLLMProvider(abc.ABC):
    """Базовый интерфейс для всех LLM-провайдеров."""

    @abc.abstractmethod
    async def complete(self, messages: list[dict[str, Any]]) -> str:
        """Отправляет запрос к LLM и возвращает ответ."""
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Закрывает сетевые соединения."""
        ...

    async def complete_with_retry(
        self,
        messages: list[dict[str, Any]],
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> str:
        """
        Отправляет запрос с автоматическими повторными попытками.

        :param messages: Список сообщений
        :param max_retries: Максимальное количество попыток
        :param base_delay: Базовая задержка между попытками (экспоненциальная)
        :return: Ответ LLM или сообщение об ошибке
        """
        for attempt in range(1, max_retries + 1):
            try:
                result = await self.complete(messages)
                # Если результат начинается с "Ошибка" — это ошибка провайдера
                if result.startswith(("HTTP-ошибка", "Ошибка соединения", "Ошибка:")):
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        log.warning(
                            "⚠️ Попытка %d/%d: %s. Повтор через %.1fс...",
                            attempt,
                            max_retries,
                            result[:80],
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    return result
                return result
            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    log.warning(
                        "⚠️ Попытка %d/%d: %s. Повтор через %.1fс...",
                        attempt,
                        max_retries,
                        str(e)[:80],
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                return f"Ошибка после {max_retries} попыток: {e}"

        return "Ошибка: неизвестная проблема"


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Провайдер для OpenAI-compatible API.
    Поддерживает: OpenAI, LM Studio, AnyLocal, и другие совместимые серверы.
    """

    def __init__(
        self,
        url: str,
        model: str,
        api_key: str | None = None,
        timeout: int = 1200,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(timeout=self.timeout)

        if api_key:
            self._client.headers["Authorization"] = f"Bearer {api_key}"

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        """Отправляет запрос к OpenAI-compatible API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            response = await self._client.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            return str(result["choices"][0]["message"]["content"])
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения: {e}"
        except (KeyError, IndexError):
            return "Ошибка: неожиданный формат ответа"

    async def close(self) -> None:
        """Закрывает клиент."""
        await self._client.aclose()


class OllamaProvider(BaseLLMProvider):
    """
    Провайдер для Ollama.
    Использует локальный Ollama-сервер.
    """

    def __init__(
        self,
        url: str = "http://127.0.0.1:11434",
        model: str = "llama3",
        timeout: int = 1200,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        """Отправляет запрос к Ollama."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            response = await self._client.post(
                f"{self.url}/api/chat", json=payload
            )
            response.raise_for_status()
            result = response.json()
            return str(result["message"]["content"])
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения: {e}"
        except (KeyError, IndexError):
            return "Ошибка: неожиданный формат ответа"

    async def close(self) -> None:
        """Закрывает клиент."""
        await self._client.aclose()


class AnthropicProvider(BaseLLMProvider):
    """
    Провайдер для Anthropic (Claude).
    Использует API Anthropic.
    """

    def __init__(
        self,
        url: str = "https://api.anthropic.com/v1/messages",
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        timeout: int = 1200,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(timeout=self.timeout)

        if api_key:
            self._client.headers["x-api-key"] = api_key
            self._client.headers["anthropic-version"] = "2023-06-01"

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        """Отправляет запрос к Anthropic."""
        # Anthropic требует отдельный system-промпт
        system_prompt = ""
        user_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            else:
                user_messages.append(msg)

        payload = {
            "model": self.model,
            "messages": user_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self._client.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            return str(result["content"][0]["text"])
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения: {e}"
        except (KeyError, IndexError):
            return "Ошибка: неожиданный формат ответа"

    async def close(self) -> None:
        """Закрывает клиент."""
        await self._client.aclose()


def create_provider(
    provider_type: str,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Фабрика для создания LLM-провайдеров.

    :param provider_type: Тип провайдера ('openai', 'ollama', 'anthropic')
    :param kwargs: Параметры для инициализации провайдера
    :return: Экземпляр провайдера
    """
    providers = {
        "openai": OpenAICompatibleProvider,
        "lm_studio": OpenAICompatibleProvider,  # LM Studio совместим с OpenAI
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ValueError(
            f"Неизвестный провайдер: {provider_type}. "
            f"Доступные: {', '.join(providers.keys())}"
        )

    return provider_class(**kwargs)


# Обратная совместимость: LLMClient теперь — это OpenAICompatibleProvider
LLMClient = OpenAICompatibleProvider
