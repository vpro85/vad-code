import httpx
from vad_code.config import settings

class LLMClient:
    """Отвечает только за сетевое взаимодействие с LLM"""
    def __init__(self) -> None:
        self.url = settings.lm_studio_url
        self.model = settings.model_name
        self.timeout = settings.timeout

    def complete(self, messages: list[dict]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        try:
            response = httpx.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            return f"HTTP-ошибка от LM Studio: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения с LM Studio: {e}"
        except (KeyError, IndexError) as e:
            return f"Ошибка: неожиданный формат ответа от LM Studio"