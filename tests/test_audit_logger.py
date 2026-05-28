"""Тесты для модуля audit_logger."""

import json
import time

import pytest

from vad_code.infrastructure.audit_logger import AuditLogger, AuditRecord


@pytest.fixture
def audit_logger():
    """Создает экземпляр AuditLogger."""
    return AuditLogger(max_records=100)


@pytest.fixture
def audit_logger_with_file(tmp_path):
    """Создает экземпляр AuditLogger с файлом аудита."""
    audit_file = tmp_path / "audit.log"
    return AuditLogger(audit_file=str(audit_file))


def test_start_and_end_call(audit_logger):
    """Проверяет регистрацию начала и завершения вызова."""
    call_id = audit_logger.start_call("read_file", {"path": "test.txt"})
    time.sleep(0.01)  # Небольшая задержка для измерения времени
    record = audit_logger.end_call(call_id, "file content", success=True)

    assert record is not None
    assert record.tool_name == "read_file"
    assert record.success is True
    assert record.duration_ms > 0
    assert len(audit_logger.records) == 1


def test_end_call_with_error(audit_logger):
    """Проверяет регистрацию ошибки."""
    call_id = audit_logger.start_call("write_file", {"path": "test.txt"})
    record = audit_logger.end_call(
        call_id, "Ошибка записи", success=False, error_message="Permission denied"
    )

    assert record.success is False
    assert record.error_message == "Permission denied"


def test_max_records_limit(audit_logger):
    """Проверяет ограничение размера журнала."""
    audit_logger.max_records = 5

    for i in range(10):
        call_id = audit_logger.start_call(f"tool_{i}", {})
        audit_logger.end_call(call_id, "result", success=True)

    assert len(audit_logger.records) == 5
    # Проверяем, что остались последние 5 записей
    assert audit_logger.records[0].tool_name == "tool_5"
    assert audit_logger.records[-1].tool_name == "tool_9"


def test_get_records_with_filter(audit_logger):
    """Проверяет фильтрацию записей."""
    for i in range(5):
        call_id = audit_logger.start_call("read_file", {})
        audit_logger.end_call(call_id, "content", success=True)

    for i in range(3):
        call_id = audit_logger.start_call("write_file", {})
        audit_logger.end_call(call_id, "ok", success=True)

    # Фильтр по имени инструмента
    read_records = audit_logger.get_records(tool_name="read_file")
    assert len(read_records) == 5

    # Фильтр по успешности
    all_records = audit_logger.get_records(success_only=True)
    assert len(all_records) == 8


def test_get_stats(audit_logger):
    """Проверяет расчет статистики."""
    for i in range(5):
        call_id = audit_logger.start_call("read_file", {})
        audit_logger.end_call(call_id, "content", success=True)

    for i in range(2):
        call_id = audit_logger.start_call("write_file", {})
        audit_logger.end_call(call_id, "ok", success=False, error_message="error")

    stats = audit_logger.get_stats()

    assert stats["total_calls"] == 7
    assert stats["successful_calls"] == 5
    assert stats["failed_calls"] == 2
    assert "read_file" in stats["tools_used"]
    assert "write_file" in stats["tools_used"]
    assert stats["tools_used"]["read_file"]["count"] == 5
    assert stats["tools_used"]["write_file"]["count"] == 2


def test_get_stats_empty(audit_logger):
    """Проверяет статистику при пустом журнале."""
    stats = audit_logger.get_stats()

    assert stats["total_calls"] == 0
    assert stats["successful_calls"] == 0
    assert stats["failed_calls"] == 0
    assert stats["avg_duration_ms"] == 0


def test_clear(audit_logger):
    """Проверяет очистку журнала."""
    call_id = audit_logger.start_call("read_file", {})
    audit_logger.end_call(call_id, "content", success=True)

    audit_logger.clear()

    assert len(audit_logger.records) == 0


def test_save_to_file(audit_logger_with_file):
    """Проверяет сохранение записей в файл."""
    call_id = audit_logger_with_file.start_call("read_file", {"path": "test.txt"})
    audit_logger_with_file.end_call(call_id, "content", success=True)

    assert audit_logger_with_file.audit_file.exists()

    # Проверяем содержимое файла
    with open(audit_logger_with_file.audit_file, "r") as f:
        line = f.readline()
        record = json.loads(line)
        assert record["tool_name"] == "read_file"
        assert record["success"] is True


def test_format_records(audit_logger):
    """Проверяет форматирование записей."""
    call_id = audit_logger.start_call("read_file", {})
    audit_logger.end_call(call_id, "file content", success=True)

    formatted = audit_logger.format_records(audit_logger.records)

    assert "read_file" in formatted
    assert "✅" in formatted


def test_format_records_empty(audit_logger):
    """Проверяет форматирование пустого журнала."""
    formatted = audit_logger.format_records([])
    assert "Нет записей" in formatted


def test_record_serialization():
    """Проверяет сериализацию/десериализацию записи."""
    record = AuditRecord(
        timestamp="2025-01-01T00:00:00",
        tool_name="read_file",
        arguments={"path": "test.txt"},
        result="content",
        success=True,
        duration_ms=10.5,
    )

    data = record.to_dict()
    restored = AuditRecord.from_dict(data)

    assert restored.tool_name == record.tool_name
    assert restored.success == record.success
    assert restored.duration_ms == record.duration_ms
