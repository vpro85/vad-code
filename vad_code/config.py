"""
Конфигурация приложения.
Поддерживает переопределение через переменные окружения (Docker, .env).
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Корневая директория проекта (переопределяется в Docker)
    project_root: str = os.getenv(
        "PROJECT_ROOT",
        str(Path(__file__).parent.parent.resolve())
    )

    # LLM настройки
    lm_studio_url: str = "http://127.0.0.1:1234/v1/chat/completions"
    model_name: str = "google/gemma-4-31b"

    # Лимиты
    max_iterations: int = 50
    max_history_messages: int = 20
    timeout: int = 1200
    max_context_tokens: int = 30000


settings = Settings()
