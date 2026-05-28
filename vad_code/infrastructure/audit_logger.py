"""
Модуль аудита действий агента.
Логирование всех вызовов инструментов с детальной информацией.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from vad_code.infrastructure.logger import log


@dataclass
class AuditRecord:
    """Запись об одном действии агента."""

    timestamp: str
    tool_name: str
    arguments: dict[str, Any]
    result: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в словарь."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditRecord":
        """Десериализация из словаря."""
        return cls(**data)


class AuditLogger:
    """
    Управляет журналом аудита действий агента.

    Хранит историю вызовов инструментов с метаданными:
    - Время вызова
    - Имя инструмента
    - Аргументы
    - Результат
    - Успех/ошибка
    - Время выполнения
    """

    def __init__(self, audit_file: Optional[str] = None, max_records: int = 1000):
        self.audit_file: Optional[Path] = Path(audit_file) if audit_file else None
        self.records: list[AuditRecord] = []
        self.max_records = max_records
        self._active_calls: dict[str, float] = {}  # tool_call_id -> start_time

    def start_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Регистрирует начало вызова инструмента.

        Args:
            tool_name: Имя вызываемого инструмента.
            arguments: Аргументы вызова.

        Returns:
            Уникальный ID вызова.
        """
        call_id = f"{tool_name}_{time.time()}"
        self._active_calls[call_id] = time.time()
        log.debug("📝 Audit: started %s(%s)", tool_name, arguments)
        return call_id

    def end_call(
        self,
        call_id: str,
        result: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> AuditRecord:
        """
        Регистрирует завершение вызова инструмента.

        Args:
            call_id: ID вызова (из start_call).
            result: Результат выполнения.
            success: Успешно ли выполнено.
            error_message: Сообщение об ошибке (если есть).

        Returns:
            Запись аудита.
        """
        start_time = self._active_calls.pop(call_id, time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Извлекаем имя инструмента из call_id
        tool_name = call_id.rsplit("_", 1)[0] if "_" in call_id else "unknown"

        record = AuditRecord(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            arguments={},  # Аргументы не сохраняем для экономии места
            result=result[:500] if result else "",  # Обрезаем длинные результаты
            success=success,
            duration_ms=round(duration_ms, 2),
            error_message=error_message,
        )

        self.records.append(record)

        # Ограничиваем размер журнала
        if len(self.records) > self.max_records:
            self.records.pop(0)

        # Сохраняем в файл, если настроен
        if self.audit_file:
            self._save_to_file(record)

        log.debug(
            "📝 Audit: %s %s (%.2fms)",
            "✅" if success else "❌",
            tool_name,
            duration_ms,
        )

        return record

    def _save_to_file(self, record: AuditRecord) -> None:
        """Сохраняет запись в файл аудита."""
        if self.audit_file is None:
            return
        try:
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.error("❌ Failed to save audit record: %s", e)

    def get_records(
        self,
        limit: int = 50,
        tool_name: Optional[str] = None,
        success_only: Optional[bool] = None,
    ) -> list[AuditRecord]:
        """
        Возвращает записи аудита с фильтрацией.

        Args:
            limit: Максимальное количество записей.
            tool_name: Фильтр по имени инструмента.
            success_only: Фильтр по успешности.

        Returns:
            Список записей.
        """
        records = self.records

        if tool_name:
            records = [r for r in records if r.tool_name == tool_name]

        if success_only is not None:
            records = [r for r in records if r.success == success_only]

        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """
        Возвращает статистику по вызовам инструментов.

        Returns:
            Словарь со статистикой.
        """
        if not self.records:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_duration_ms": 0,
                "tools_used": {},
            }

        total = len(self.records)
        successful = sum(1 for r in self.records if r.success)
        failed = total - successful
        avg_duration = sum(r.duration_ms for r in self.records) / total

        # Статистика по каждому инструменту
        tools_stats: dict[str, dict[str, Any]] = {}
        for record in self.records:
            if record.tool_name not in tools_stats:
                tools_stats[record.tool_name] = {
                    "count": 0,
                    "success": 0,
                    "failed": 0,
                    "total_duration_ms": 0,
                }
            stats = tools_stats[record.tool_name]
            stats["count"] += 1
            stats["total_duration_ms"] += record.duration_ms
            if record.success:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        # Вычисляем среднее время для каждого инструмента
        for tool, stats in tools_stats.items():
            stats["avg_duration_ms"] = round(
                stats["total_duration_ms"] / stats["count"], 2
            )

        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": failed,
            "avg_duration_ms": round(avg_duration, 2),
            "tools_used": tools_stats,
        }

    def clear(self) -> None:
        """Очищает журнал."""
        self.records.clear()
        log.info("🧹 Журнал аудита очищен.")

    def format_records(self, records: list[AuditRecord]) -> str:
        """
        Форматирует записи для отображения.

        Args:
            records: Список записей.

        Returns:
            Форматированная строка.
        """
        if not records:
            return "Нет записей в журнале."

        lines = []
        for i, record in enumerate(records, 1):
            status = "✅" if record.success else "❌"
            lines.append(
                f"  {i}. {status} {record.tool_name} "
                f"({record.duration_ms}ms) "
                f"[{record.timestamp}]"
            )
            if record.error_message:
                lines.append(f"     Ошибка: {record.error_message}")
            if record.result and len(record.result) < 200:
                preview = record.result.replace("\n", " ")
                lines.append(f"     Результат: {preview[:150]}")

        return "\n".join(lines)


# Глобальный экземпляр
audit_logger = AuditLogger()
