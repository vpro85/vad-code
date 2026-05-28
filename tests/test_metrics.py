"""Тесты для модуля метрик."""

import time
import pytest

from vad_code.infrastructure.metrics import (
    ToolMetrics,
    TokenMetrics,
    SessionMetrics,
    session_metrics,
    reset_metrics,
    get_metrics,
    record_tool_call,
    record_tokens,
    format_metrics,
)


@pytest.fixture(autouse=True)
def clean_metrics():
    """Сбрасывает метрики перед каждым тестом."""
    reset_metrics()
    yield
    reset_metrics()


def test_tool_metrics_initial():
    """Проверяет начальные значения метрик инструмента."""
    tm = ToolMetrics(name="test_tool")
    assert tm.call_count == 0
    assert tm.success_count == 0
    assert tm.error_count == 0
    assert tm.avg_execution_time == 0.0
    assert tm.success_rate == 100.0


def test_tool_metrics_after_calls():
    """Проверяет метрики после вызовов."""
    tm = ToolMetrics(name="test_tool")
    tm.call_count = 5
    tm.success_count = 4
    tm.error_count = 1
    tm.total_execution_time = 10.0
    tm.min_execution_time = 1.0
    tm.max_execution_time = 5.0

    assert tm.avg_execution_time == 2.0
    assert tm.success_rate == 80.0


def test_token_metrics_initial():
    """Проверяет начальные значения метрик токенов."""
    tm = TokenMetrics()
    assert tm.total_tokens == 0
    assert tm.request_count == 0
    assert tm.avg_prompt_tokens == 0.0


def test_token_metrics_after_requests():
    """Проверяет метрики токенов после запросов."""
    tm = TokenMetrics()
    tm.total_prompt_tokens = 1000
    tm.total_completion_tokens = 500
    tm.total_tokens = 1500
    tm.request_count = 3

    assert tm.avg_prompt_tokens == pytest.approx(333.33, abs=0.01)
    assert tm.avg_completion_tokens == pytest.approx(166.67, abs=0.01)


def test_session_metrics_initial():
    """Проверяет начальные значения метрик сессии."""
    sm = SessionMetrics()
    assert sm.total_tool_calls == 0
    assert sm.total_errors == 0
    assert sm.error_rate == 0.0
    assert sm.session_duration >= 0


def test_session_record_tool_call():
    """Проверяет регистрацию вызова инструмента."""
    sm = SessionMetrics()
    sm.record_tool_call("test_tool", 1.5, success=True)

    assert sm.total_tool_calls == 1
    assert sm.total_errors == 0
    assert "test_tool" in sm.tool_metrics
    assert sm.tool_metrics["test_tool"].call_count == 1


def test_session_record_tool_call_error():
    """Проверяет регистрацию ошибки инструмента."""
    sm = SessionMetrics()
    sm.record_tool_call("test_tool", 0.5, success=False)

    assert sm.total_tool_calls == 1
    assert sm.total_errors == 1
    assert sm.error_rate == 100.0


def test_session_record_tokens():
    """Проверяет регистрацию токенов."""
    sm = SessionMetrics()
    sm.record_tokens(100, 50)

    assert sm.token_metrics.total_tokens == 150
    assert sm.token_metrics.request_count == 1


def test_session_format_summary():
    """Проверяет форматирование сводки."""
    sm = SessionMetrics()
    sm.record_tool_call("read_file", 0.1, success=True)
    sm.record_tool_call("write_file", 0.2, success=True)
    sm.record_tokens(200, 100)

    summary = sm.format_summary()
    assert "📊 Метрики сессии" in summary
    assert "read_file" in summary
    assert "write_file" in summary
    assert "Токены" in summary


def test_reset_metrics():
    """Проверяет сброс метрик."""
    record_tool_call("test", 1.0, success=True)
    reset_metrics()

    metrics = get_metrics()
    assert metrics.total_tool_calls == 0


def test_global_functions():
    """Проверяет глобальные функции."""
    record_tool_call("global_test", 0.5, success=True)
    record_tokens(50, 25)

    metrics = get_metrics()
    assert metrics.total_tool_calls == 1
    assert metrics.token_metrics.total_tokens == 75

    summary = format_metrics()
    assert "global_test" in summary


def test_multiple_tool_calls_same_tool():
    """Проверяет несколько вызовов одного инструмента."""
    sm = SessionMetrics()
    sm.record_tool_call("read_file", 0.1, success=True)
    sm.record_tool_call("read_file", 0.2, success=True)
    sm.record_tool_call("read_file", 0.3, success=False)

    tm = sm.tool_metrics["read_file"]
    assert tm.call_count == 3
    assert tm.success_count == 2
    assert tm.error_count == 1
    assert tm.avg_execution_time == pytest.approx(0.2, abs=0.01)
    assert tm.min_execution_time == 0.1
    assert tm.max_execution_time == 0.3


def test_session_duration():
    """Проверяет измерение длительности сессии."""
    sm = SessionMetrics()
    time.sleep(0.1)  # небольшая задержка
    assert sm.session_duration >= 0.1
