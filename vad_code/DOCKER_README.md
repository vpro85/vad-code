# 🐳 Docker-развёртывание AI-агента vad-code

## Архитектура

```
┌─────────────────────────────────────────────────┐
│              Host Machine                        │
│                                                  │
│  ┌──────────────┐    ┌──────────────────────┐   │
│  │   workspace/ │◄──►│  vad-code-agent       │   │
│  │  (volume)    │     │  (Python 3.14)       │   │
│  └──────────────┘     │  - git               │   │
│                       │  - curl               │   │
│                       │  - uv/pip             │   │
│                       └──────────┬───────────┘   │
│                                  │ HTTP          │
│                       ┌──────────▼───────────┐   │
│                       │  LM Studio (Host)     │   │
│                       │  (Local Installation) │   │
│                       └──────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Быстрый старт

### 1. Подготовка

Убедись, что LM Studio запущен локально и слушает порт `1234`:
- Открой LM Studio
- Перейди в раздел \"Local Server\"
- Убедись, что модель загружена
- Проверь, что URL: `http://127.0.0.1:1234/v1/chat/completions`

### 2. Сборка и запуск

```bash
# Собрать образ и запустить контейнер
docker compose up --build

# Или в фоне
docker compose up -d --build
```

### 3. Подключение к агенту

```bash
# Подключиться к консоли агента
docker compose exec agent python -m vad_code

# Или открыть интерактивный shell
docker compose exec agent bash
```

### 4. Остановка

```bash
# Остановить контейнер (данные в workspace сохраняются)
docker compose down

# Остановить и удалить контейнер
docker compose down --remove-orphans
```

## Структура volumes

| Volume | Mount Point | Описание |
|--------|-------------|----------|
| `./workspace` | `/workspace` | Рабочая директория агента (персистентная) |

## Настройка через переменные окружения

Все настройки можно переопределить в `docker-compose.yml` или через `.env`:

```yaml
environment:
  - PROJECT_ROOT=/workspace
  - LM_STUDIO_URL=http://host.docker.internal:1234/v1/chat/completions
  - MODEL_NAME=google/gemma-4-31b
  - MAX_ITERATIONS=50
  - MAX_HISTORY_MESSAGES=20
  - TIMEOUT=1200
  - MAX_CONTEXT_TOKENS=30000
```

## Безопасность

### Ограничения ресурсов

В `docker-compose.yml` настроены лимиты:
- **CPU**: до 2 ядер
- **RAM**: до 4 GB
- **Минимум**: 0.5 CPU, 512 MB RAM

### Сетевая изоляция

Контейнер агента имеет доступ только к:
- LM Studio на хост-машине (через `host.docker.internal`)
- Файловой системе `/workspace`

### Безопасные операции

Благодаря Docker-изоляции агент может:
- ✅ Запускать **любые** команды внутри контейнера
- ✅ Устанавливать пакеты (`pip install`, `npm install`)
- ✅ Модифицировать файловую систему `/workspace`
- ✅ Создавать/удалять директории

Но **не может**:
- ❌ Выходить за пределы `/workspace`
- ❌ Получать доступ к файлам хоста (кроме смонтированных volumes)
- ❌ Превышать лимиты ресурсов

## Разработка

### Hot-reload кода агента

Для разработки раскомментируй в `docker-compose.yml`:

```yaml
volumes:
  - ./vad_code:/app/vad_code  # Hot-reload
```

### Логи

```bash
# Посмотреть логи агента
docker compose logs agent

# Следить за логами в реальном времени
docker compose logs -f agent
```

## Troubleshooting

### Ошибка подключения к LM Studio

```bash
# Проверь, что LM Studio запущен локально
curl http://127.0.0.1:1234/v1/chat/completions

# Проверь, что контейнер видит хост
docker compose exec agent ping host.docker.internal
```

### Не хватает памяти

Увеличь лимиты в `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 8G  # Увеличить до 8 GB
```

### Ошибка прав доступа к workspace

```bash
# Убедись, что директория workspace существует
mkdir -p workspace

# Проверь права
chmod 755 workspace
```

## Продвинутые настройки

### Добавление новых инструментов в контейнер

Если агенту нужны дополнительные утилиты, добавь их в `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \\
    nodejs \\
    npm \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*
```

### Персистентность истории сессий

Смонтируй дополнительную volume для логов:

```yaml
volumes:
  - ./logs:/app/logs
```

---

**Версия**: 1.0.0  
**Python**: 3.14-slim  
**Обновлено**: 2025
"}}
