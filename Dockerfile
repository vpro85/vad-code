# ==============================================================================
# Dockerfile для AI-агента vad-code
# ==============================================================================

FROM python:3.14-slim

# Метки образа
LABEL maintainer="vad-code"
LABEL description="AI Agent for file system operations"

# Переменные сборки
ARG INSTALL_DEPS=true

# Рабочая директория
WORKDIR /app

# Системные зависимости (git, curl для возможных нужд агента)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем файлы зависимостей отдельно для кэширования Docker-слоёв
COPY pyproject.toml uv.lock ./

# Устанавливаем uv и зависимости
RUN pip install --no-cache-dir uv \
    && uv sync --frozen

# Копируем код проекта
COPY . .

# Создаём рабочую директорию для проектов агента
RUN mkdir -p /workspace

# Устанавливаем переменные окружения по умолчанию
ENV PROJECT_ROOT=/workspace \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Точка входа
ENTRYPOINT ["python", "-m", "vad_code"]

# Документация
CMD []
