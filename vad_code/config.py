from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    project_root: str = str(Path(__file__).parent.parent.resolve())
    lm_studio_url: str = "http://127.0.0.1:1234/v1/chat/completions"
    model_name: str = "google/gemma-4-31b"
    max_iterations: int = 50
    max_history_messages: int = 20
    timeout: int = 1200
    max_context_tokens: int = 8192


settings = Settings()
