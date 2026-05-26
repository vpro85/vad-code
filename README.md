# 🤖 vad-code — AI-инженер для локальной разработки

Локальный AI-агент, способный анализировать и изменять код через взаимодействие с LLM. Поддерживает LM Studio, Ollama, OpenAI и Anthropic.

## 📂 Структура проекта

```
vad_code/
├── core/           # Ядро агента
│   ├── agent.py       # Основной цикл, системный промпт, извлечение вызовов
│   ├── executor.py    # Исполнитель инструментов с валидацией аргументов
│   └── memory.py      # Управление историей и обрезка контекста
├── infrastructure/   # Базовые сервисы
│   ├── llm_providers.py  # Абстракция LLM-провайдеров (OpenAI, Ollama, Anthropic)
│   ├── llm_client.py     # HTTP-клиент для OpenAI-совместимых API
│   ├── file_system.py    # Безопасная работа с ФС (защита от path traversal)
│   ├── tokenizer.py      # Подсчет токенов (transformers)
│   └── logger.py         # Логирование
├── tools/            # Инструменты агента
│   ├── file_tools.py     # 21 инструмент для работы с файлами
│   ├── git_tools.py      # Инструменты для Git
│   └── schemas.py        # Pydantic-схемы для валидации
├── config.py         # Настройки (Pydantic Settings)
└── __main__.py       # Точка входа (asyncio)
```

## ⚙️ Ключевые особенности

- **Мульти-провайдерная архитектура**: поддержка LM Studio, Ollama, OpenAI, Anthropic
- **21 инструмент для работы с файлами**: `list_files`, `read_file`, `write_file`, `search_in_files`, `run_command` и др.
- **Git-интеграция**: инструменты для `git status`, `commit`, `diff`, `branch` и т.д.
- **Безопасность**: `FileSystemService` не позволяет выйти за пределы рабочей директории
- **Валидация**: аргументы инструментов проверяются через Pydantic-схемы
- **Кэширование**: LRU-кэш для содержимого файлов
- **Управление контекстом**: автоматическая обрезка истории по токенам

## 🚀 Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd vad-code

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Установить зависимости
pip install -e .
```

## ⚙️ Конфигурация

Создайте файл `.env` в корне проекта:

```env
# Тип провайдера: openai, ollama, anthropic, lm_studio
LLM_PROVIDER=openai

# URL API
LLM_URL=http://127.0.0.1:1234/v1/chat/completions

# Модель
LLM_MODEL=qwen/qwen3.6-27b

# API-ключ (для OpenAI/Anthropic)
#LLM_API_KEY=sk-...

# Параметры генерации
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# Лимиты
MAX_ITERATIONS=100
MAX_HISTORY_MESSAGES=100
TIMEOUT=1200
MAX_CONTEXT_TOKENS=30000

# Рабочая директория (по умолчанию — корень проекта)
#PROJECT_ROOT=/path/to/project
```

### Примеры конфигурации

**LM Studio:**
```env
LLM_PROVIDER=openai
LLM_URL=http://127.0.0.1:1234/v1/chat/completions
LLM_MODEL=qwen/qwen3.6-27b
```

**Ollama:**
```env
LLM_PROVIDER=ollama
LLM_URL=http://127.0.0.1:11434
LLM_MODEL=llama3
```

**Anthropic:**
```env
LLM_PROVIDER=anthropic
LLM_URL=https://api.anthropic.com/v1/messages
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-...
```

## 🎮 Использование

```bash
python -m vad_code
```

Агент работает в интерактивном режиме:

```
Вы: Изучи проект
AI: [анализ структуры проекта...]

Вы: Добавь новый инструмент для поиска по git-логу
AI: [реализация инструмента...]
```

### Команды

- `/reset` — сбросить историю разговора
- `exit` / `quit` — выйти из агента

## 🧪 Тесты

```bash
pytest tests/ -v
```

## 📦 Docker

```bash
docker build -t vad-code .
docker run -it --env-file .env vad-code
```

## 🗺️ Дорожная карта

### ✅ Реализовано (v0.3.0)
- Мульти-провайдерная архитектура
- 21 инструмент для работы с файлами
- Git-интеграция (15+ команд)
- Валидация аргументов через Pydantic
- Безопасная работа с ФС
- LRU-кэширование
- Управление контекстом
- Retry-логика для LLM-запросов
- Строгая типизация (mypy strict)
- Линтинг (pylint 10/10, flake8)
- Тестовое покрытие (112 теста)
- Конфигурация линтеров в `pyproject.toml` (убраны `.flake8` и `mypy.ini`)

### 🚧 В планах
- Инструменты `install_package`, `run_tests`, `format_code`
- CLI-аргументы
- Мульти-агентная архитектура
- Векторная база знаний
- Веб-интерфейс
- IDE-интеграция

## 📄 Лицензия

MIT

## 🤝 Вклад

Принимаю pull requests! Для крупных изменений откройте issue для обсуждения.
