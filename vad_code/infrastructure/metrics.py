"""
Модуль мониторинга и метрик.
Сбор статистики по вызовам инструментов, токенам, времени отклика.
"""
import time
from dataclasses import dataclass, field

from vad_code.infrastructure.logger import log


@dataclass
class ToolMetrics:
    """Метрики для одного инструмента."""
    name: str
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_execution_time: float = 0.0  # секунды
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0

    @property
    def avg_execution_time(self) -> float:
        """Среднее время выполнения."""
        if self.call_count == 0:
            return 0.0
        return self.total_execution_time / self.call_count

    @property
    def success_rate(self) -> float:
        """Процент успешных вызовов."""
        if self.call_count == 0:
            return 100.0
        return (self.success_count / self.call_count) * 100


@dataclass
class TokenMetrics:
    """Метрики использования токенов."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0

    @property
    def avg_prompt_tokens(self) -> float:
        """Среднее количество токенов в промпте."""
        if self.request_count == 0:
            return 0.0
        return self.total_prompt_tokens / self.request_count

    @property
    def avg_completion_tokens(self) -> float:
        """Среднее количество токенов в ответе."""
        if self.request_count == 0:
            return 0.0
        return self.total_completion_tokens / self.request_count


@dataclass
class SessionMetrics:
    """Метрики сессии."""
    start_time: float = field(default_factory=time.time)
    total_tool_calls: int = 0
    total_errors: int = 0
    tool_metrics: dict[str, ToolMetrics] = field(default_factory=dict)
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)

    @property
    def session_duration(self) -> float:
        """Длительность сессии в секундах."""
        return time.time() - self.start_time

    @property
    def error_rate(self) -> float:
        """Процент ошибок."""
        if self.total_tool_calls == 0:
            return 0.0
        return (self.total_errors / self.total_tool_calls) * 100

    def get_or_create_tool_metrics(self, tool_name: str) -> ToolMetrics:
        """Получает или создает метрики для инструмента."""
        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = ToolMetrics(name=tool_name)
        return self.tool_metrics[tool_name]

    def record_tool_call(self, tool_name: str, execution_time: float, success: bool) -> None:
        """Регистрирует вызов инструмента."""
        metrics = self.get_or_create_tool_metrics(tool_name)
        metrics.call_count += 1
        metrics.total_execution_time += execution_time
        metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)

        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
            self.total_errors += 1

        self.total_tool_calls += 1

    def record_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Регистрирует использование токенов."""
        self.token_metrics.total_prompt_tokens += prompt_tokens
        self.token_metrics.total_completion_tokens += completion_tokens
        self.token_metrics.total_tokens += prompt_tokens + completion_tokens
        self.token_metrics.request_count += 1

    def format_summary(self) -> str:
        """Форматирует сводку метрик."""
        lines = [
            "📊 Метрики сессии",
            "=" * 50,
            f"⏱️ Длительность: {self.session_duration:.1f}с",
            f"🛠️ Всего вызовов инструментов: {self.total_tool_calls}",
            f"❌ Ошибок: {self.total_errors} ({self.error_rate:.1f}%)",
            "",
        ]

        # Токены
        if self.token_metrics.request_count > 0:
            tm = self.token_metrics
            lines.extend([
                "📝 Токены",
                "-" * 30,
                f"  Запросов к LLM: {tm.request_count}",
                f"  Токенов в промптах: {tm.total_prompt_tokens:,}",
                f"  Токенов в ответах: {tm.total_completion_tokens:,}",
                f"  Всего токенов: {tm.total_tokens:,}",
                f"  Среднее на запрос: {tm.avg_prompt_tokens:.0f} + {tm.avg_completion_tokens:.0f}",
                "",
            ])

        # Метрики по инструментам
        if self.tool_metrics:
            lines.extend([
                "🛠️ Метрики по инструментам",
                "-" * 30,
            ])
            # Сортируем по количеству вызовов (по убыванию)
            sorted_tools = sorted(
                self.tool_metrics.values(),
                key=lambda m: m.call_count,
                reverse=True
            )
            for tool_metric in sorted_tools:
                lines.append(
                    f"  {tool_metric.name}: {tool_metric.call_count} вызовов, "
                    f"успех {tool_metric.success_rate:.0f}%, "
                    f"среднее время {tool_metric.avg_execution_time:.2f}с "
                    f"(min: {tool_metric.min_execution_time:.2f}с, max: {tool_metric.max_execution_time:.2f}с)"
                )
            lines.append("")

        return "\n".join(lines)


# Глобальный экземпляр метрик
session_metrics = SessionMetrics()


def reset_metrics() -> None:
    """Сбрасывает все метрики."""
    global session_metrics
    session_metrics = SessionMetrics()
    log.info("📊 Метрики сброшены")


def get_metrics() -> SessionMetrics:
    """Возвращает текущие метрики сессии."""
    return session_metrics


def record_tool_call(tool_name: str, execution_time: float, success: bool) -> None:
    """Удобная функция для регистрации вызова инструмента."""
    session_metrics.record_tool_call(tool_name, execution_time, success)


def record_tokens(prompt_tokens: int, completion_tokens: int) -> None:
    """Удобная функция для регистрации токенов."""
    session_metrics.record_tokens(prompt_tokens, completion_tokens)


def format_metrics() -> str:
    """Удобная функция для форматирования метрик."""
    return session_metrics.format_summary()
