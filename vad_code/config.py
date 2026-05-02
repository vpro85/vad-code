import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# =================== Настройки ===================
PROJECT_ROOT = str(Path(__file__).parent.parent.resolve())
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-31b")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 50))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 20))
TIMEOUT = int(os.getenv("TIMEOUT", 1200))

# =================================================
