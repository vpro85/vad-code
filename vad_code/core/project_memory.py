"""
Проектная память - сохранение знаний между сессиями.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vad_code.infrastructure.logger import log


@dataclass
class ProjectMemoryEntry:
    """Запись в памяти проекта."""

    key: str
    value: str
    category: str  # "architecture", "convention", "decision", "fact"
    timestamp: float = 0.0
    confidence: float = 1.0


class ProjectMemory:
    """Управление знаниями о проекте между сессиями."""

    def __init__(self, project_root: str, memory_file: str | None = None) -> None:
        self.project_root = Path(project_root)
        self.memory_file = (
            Path(memory_file)
            if memory_file
            else self.project_root / ".vad_code_memory.json"
        )
        self.entries: dict[str, ProjectMemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        """Загружает память из файла."""
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text(encoding="utf-8"))
                for key, entry_data in data.items():
                    self.entries[key] = ProjectMemoryEntry(**entry_data)
                log.info(
                    "📚 Загружено %d записей из проектной памяти",
                    len(self.entries),
                )
            except Exception as e:
                log.warning("⚠️ Не удалось загрузить проектную память: %s", e)
                self.entries = {}

    def save(self) -> None:
        """Сохраняет память в файл."""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                key: {
                    "key": entry.key,
                    "value": entry.value,
                    "category": entry.category,
                    "timestamp": entry.timestamp,
                    "confidence": entry.confidence,
                }
                for key, entry in self.entries.items()
            }
            self.memory_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.debug("💾 Проектная память сохранена (%d записей)", len(self.entries))
        except Exception as e:
            log.error("❌ Не удалось сохранить проектную память: %s", e)

    def add(self, key: str, value: str, category: str, confidence: float = 1.0) -> None:
        """Добавляет запись в память."""
        import time

        self.entries[key] = ProjectMemoryEntry(
            key=key,
            value=value,
            category=category,
            timestamp=time.time(),
            confidence=confidence,
        )
        log.debug("📝 Добавлена запись в память: %s", key)

    def get(self, key: str) -> ProjectMemoryEntry | None:
        """Получает запись по ключу."""
        return self.entries.get(key)

    def search(self, query: str) -> list[ProjectMemoryEntry]:
        """Ищет записи по тексту."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            if query_lower in entry.key.lower() or query_lower in entry.value.lower():
                results.append(entry)
        return results

    def get_by_category(self, category: str) -> list[ProjectMemoryEntry]:
        """Получает все записи категории."""
        return [
            entry
            for entry in self.entries.values()
            if entry.category == category
        ]

    def get_context_prompt(self) -> str:
        """Формирует промпт с контекстом из памяти проекта."""
        if not self.entries:
            return ""

        lines = ["## Контекст проекта:"]

        # Архитектурные решения
        arch_entries = self.get_by_category("architecture")
        if arch_entries:
            lines.append("\n### Архитектура:")
            for entry in arch_entries[:5]:
                lines.append(f"- {entry.value}")

        # Конвенции
        conv_entries = self.get_by_category("convention")
        if conv_entries:
            lines.append("\n### Конвенции:")
            for entry in conv_entries[:5]:
                lines.append(f"- {entry.value}")

        # Решения
        decision_entries = self.get_by_category("decision")
        if decision_entries:
            lines.append("\n### Принятые решения:")
            for entry in decision_entries[:5]:
                lines.append(f"- {entry.value}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Очищает память."""
        self.entries = {}
        self.save()
        log.info("🧹 Проектная память очищена.")

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику памяти."""
        categories: dict[str, int] = {}
        for entry in self.entries.values():
            categories[entry.category] = categories.get(entry.category, 0) + 1

        return {
            "total_entries": len(self.entries),
            "categories": categories,
            "memory_file": str(self.memory_file),
        }
