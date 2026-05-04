import httpx

from vad_code.config import settings


class LLMClient:
    """Отвечает только за сетевое взаимодействие с LLM"""

    def __init__(self) -> None:
        self.url = settings.lm_studio_url
        self.model = settings.model_name
        self.timeout = settings.timeout
        # Создаем один клиент для всех запросов (Connection Pooling)
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def complete(self, messages: list[dict]) -> str:  # Изменено на async
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        try:
            # Используем существующий клиент вместо создания нового
            response = await self._client.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка от LM Studio: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения с LM Studio: {e}"
        except (KeyError, IndexError) as e:
            return f"Ошибка: неожиданный формат ответа от LM Studio"

    async def close(self) -> None:
        """Метод для корректного закрытия клиента при завершении работы приложения"""
        await self._client.aclose()
