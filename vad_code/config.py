"""
Конфигурация приложения.
Поддерживает переопределение через переменные окружения (Docker, .env).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Корневая директория проекта (переопределяется через PROJECT_ROOT)
    project_root: str = str(Path(__file__).parent.parent.resolve())

    # LLM настройки
    llm_provider: str = "openai"
    llm_url: str = "http://127.0.0.1:1234/v1/chat/completions"
    llm_model: str = "google/gemma-4-31b"
    llm_api_key: str | None = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Лимиты
    max_iterations: int = 50
    max_history_messages: int = 20
    timeout: int = 1200
    max_context_tokens: int = 30000

    # Безопасность
    # Допустимые уровни риска инструментов: read, write, dangerous
    # По умолчанию разрешены все уровни
    allowed_tool_risk_levels: str = "read,write,dangerous"

    # Мульти-агентный режим
    enable_multi_agent: bool = True


settings = Settings()
