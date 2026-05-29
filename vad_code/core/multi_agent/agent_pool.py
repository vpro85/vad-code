"""Пул агентов для параллельного выполнения задач."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from vad_code.core.multi_agent.base_agent import AgentType, BaseAgent
from vad_code.core.multi_agent.orchestrator import TaskResult
from vad_code.infrastructure.logger import log


@dataclass
class WorkerConfig:
    """Конфигурация рабочего процесса."""

    max_concurrent_tasks: int = 3
    task_timeout: float = 120.0  # секунд
    retry_on_failure: bool = True
    max_retries: int = 2


class AgentPool:
    """Пул агентов для масштабирования и параллельного выполнения.

    Функции:
    - Управление пулом рабочих агентов
    - Балансировка нагрузки
    - Очереди задач
    - Автоматическое масштабирование
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        config: WorkerConfig | None = None,
    ) -> None:
        """
        Инициализация пула агентов.

        :param agents: Список агентов для пула
        :param config: Конфигурация пула
        """
        self._agents = agents
        self._config = config or WorkerConfig()

        # Очередь задач
        self._task_queue: asyncio.Queue[tuple[str, dict[str, Any] | None]] = (
            asyncio.Queue()
        )

        # Активные задачи
        self._active_tasks: dict[str, asyncio.Task] = {}

        # Статистика
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
        }

        # Флаги управления
        self._running = False
        self._workers: list[asyncio.Task] = []

        log.info(
            f"🏊 Пул агентов создан: {len(agents)} агентов, "
            f"макс. параллельность: {self._config.max_concurrent_tasks}"
        )

    @property
    def agents(self) -> list[BaseAgent]:
        """Возвращает список агентов в пуле."""
        return self._agents

    @property
    def is_running(self) -> bool:
        """Проверяет, работает ли пул."""
        return self._running

    def submit_task(self, task: str, context: dict[str, Any] | None = None) -> None:
        """
        Добавляет задачу в очередь.

        :param task: Описание задачи
        :param context: Контекст задачи
        """
        self._task_queue.put_nowait((task, context))
        self.stats["tasks_submitted"] += 1
        log.debug(f"📋 Задача добавлена в очередь (всего: {self._task_queue.qsize()})")

    async def process_next(self) -> TaskResult | None:
        """
        Обрабатывает следующую задачу из очереди.

        :return: Результат или None, если очередь пуста
        """
        if self._task_queue.empty():
            return None

        task, context = self._task_queue.get_nowait()

        # Выбираем агента с наименьшей нагрузкой
        agent = self._select_agent()
        if not agent:
            return TaskResult(
                agent_type=AgentType.GENERAL,
                success=False,
                result="",
                execution_time_ms=0,
                error="Нет доступных агентов",
            )

        try:
            result = await asyncio.wait_for(
                agent.handle_task(task, context),
                timeout=self._config.task_timeout,
            )

            self.stats["tasks_completed"] += 1
            agent.stats["tasks_completed"] += 1

            return TaskResult(
                agent_type=agent.agent_type,
                success=True,
                result=result,
                execution_time_ms=0,  # Будет заполнено агентом
            )

        except asyncio.TimeoutError:
            self.stats["tasks_failed"] += 1
            log.error(f"⏱️ Таймаут выполнения задачи: {task[:50]}...")
            return TaskResult(
                agent_type=agent.agent_type,
                success=False,
                result="",
                execution_time_ms=self._config.task_timeout * 1000,
                error="Превышено время выполнения",
            )

        except Exception as e:
            self.stats["tasks_failed"] += 1
            log.error(f"❌ Ошибка выполнения задачи: {e}")

            # Повторная попытка
            if self._config.retry_on_failure:
                return await self._retry_task(task, context)

            return TaskResult(
                agent_type=agent.agent_type,
                success=False,
                result="",
                execution_time_ms=0,
                error=str(e),
            )

    async def _retry_task(
        self, task: str, context: dict[str, Any] | None
    ) -> TaskResult:
        """Повторяет выполнение задачи."""
        self.stats["tasks_retried"] += 1
        log.info(f"🔄 Повторная попытка выполнения задачи")

        for attempt in range(self._config.max_retries):
            try:
                agent = self._select_agent()
                if not agent:
                    break

                result = await agent.handle_task(task, context)
                self.stats["tasks_completed"] += 1

                return TaskResult(
                    agent_type=agent.agent_type,
                    success=True,
                    result=result,
                    execution_time_ms=0,
                )

            except Exception:
                log.warning(f"⚠️ Попытка {attempt + 1}/{self._config.max_retries} не удалась")
                continue

        return TaskResult(
            agent_type=AgentType.GENERAL,
            success=False,
            result="",
            execution_time_ms=0,
            error=f"Все {self._config.max_retries} попыток не удались",
        )

    def _select_agent(self) -> BaseAgent | None:
        """
        Выбирает агента с наименьшей нагрузкой.

        :return: Агент или None
        """
        if not self._agents:
            return None

        # Простая балансировка: выбираем агента с наименьшим количеством
        # выполненных задач
        return min(
            self._agents,
            key=lambda a: a.stats["tasks_completed"],
        )

    async def process_all(self) -> list[TaskResult]:
        """
        Обрабатывает все задачи в очереди.

        :return: Список результатов
        """
        results: list[TaskResult] = []

        while not self._task_queue.empty():
            result = await self.process_next()
            if result:
                results.append(result)

        return results

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику пула."""
        return {
            **self.stats,
            "queue_size": self._task_queue.qsize(),
            "agents_count": len(self._agents),
            "agents_info": [
                {
                    "type": agent.agent_type.value,
                    "tasks_completed": agent.stats["tasks_completed"],
                    "errors": agent.stats["errors"],
                }
                for agent in self._agents
            ],
        }

    def clear_queue(self) -> None:
        """Очищает очередь задач."""
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        log.info("🧹 Очередь задач очищена")
