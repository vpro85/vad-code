# Пресеты конфигураций для vad-code

Готовые файлы конфигурации для популярных LLM-провайдеров.

## 📋 Доступные пресеты

| Пресет | Файл | Описание |
|--------|------|----------|
| OpenAI GPT-4 | `.env.openai-gpt4` | GPT-4 через OpenAI API |
| OpenAI GPT-4o | `.env.openai-gpt4o` | GPT-4o (оптимизированная модель) |
| Ollama (локально) | `.env.ollama` | Локальные модели через Ollama |
| Anthropic Claude | `.env.anthropic` | Claude через Anthropic API |
| LM Studio | `.env.lm-studio` | Локальные модели через LM Studio |

## 🚀 Как использовать

1. Скопируйте нужный пресет в `.env`:
```bash
cp presets/.env.ollama .env
```

2. Или укажите путь к пресету при запуске:
```bash
python -m vad_code --config presets/.env.ollama
```

3. Отредактируйте `.env` при необходимости (API-ключи, модель и т.д.)

## ⚙️ Настройки

Основные параметры в `.env`:

| Параметр | Описание | Пример |
|----------|----------|--------|
| `LLM_PROVIDER` | Провайдер LLM | `openai`, `ollama`, `anthropic`, `lm_studio` |
| `LLM_URL` | URL API-эндпоинта | `http://127.0.0.1:11434/v1/chat/completions` |
| `LLM_MODEL` | Название модели | `gpt-4`, `llama3`, `claude-3-opus` |
| `LLM_API_KEY` | API-ключ (если нужен) | `sk-...` |
| `LLM_TEMPERATURE` | Температура генерации | `0.1` (детерминированно) - `1.0` (креативно) |
| `LLM_MAX_TOKENS` | Макс. токенов в ответе | `4096` |
| `MAX_ITERATIONS` | Макс. итераций на запрос | `50` |
| `TIMEOUT` | Таймаут (секунды) | `1200` |
| `ALLOWED_TOOL_RISK_LEVELS` | Уровни риска инструментов | `read,write,dangerous` |

## 🔒 Безопасность

- Никогда не коммитьте `.env` с реальными API-ключами
- Используйте переменные окружения для чувствительных данных
- Для локальных моделей (Ollama, LM Studio) API-ключ не нужен
