"""Модуль для сбора и анализа проблемных случаев распознавания команд."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from vad_code.config import settings
from vad_code.infrastructure.logger import log

BAD_CASES_FILE = os.path.join(settings.project_root, "workspace", "bad_cases.json")


@dataclass
class BadCase:
    """Проблемный случай распознавания команды."""

    id: str
    timestamp: str
    user_input: str
    ai_response: str
    error_type: str  # parse_error, missing_tool_key, invalid_json, no_call_detected
    error_details: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BadCase":
        return cls(**data)


class BadCaseManager:
    """Управляет коллекцией проблемных случаев."""

    def __init__(self) -> None:
        self.cases: list[BadCase] = []
        self._load()

    def _load(self) -> None:
        """Загружает сохраненные случаи из файла."""
        if os.path.exists(BAD_CASES_FILE):
            try:
                with open(BAD_CASES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cases = [BadCase.from_dict(item) for item in data]
                log.debug(f"Загружено {len(self.cases)} проблемных случаев")
            except (json.JSONDecodeError, KeyError) as e:
                log.error(f"Ошибка загрузки bad_cases.json: {e}")
                self.cases = []

    def _save(self) -> None:
        """Сохраняет случаи в файл."""
        os.makedirs(os.path.dirname(BAD_CASES_FILE), exist_ok=True)
        try:
            with open(BAD_CASES_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    [case.to_dict() for case in self.cases],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            log.debug(f"Сохранено {len(self.cases)} проблемных случаев")
        except OSError as e:
            log.error(f"Ошибка сохранения bad_cases.json: {e}")

    def add_case(
        self,
        user_input: str,
        ai_response: str,
        error_type: str,
        error_details: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Добавляет новый проблемный случай.

        :return: ID созданного случая
        """
        case_id = (
            f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.cases) + 1}"
        )
        case = BadCase(
            id=case_id,
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            ai_response=ai_response,
            error_type=error_type,
            error_details=error_details,
            context=context or {},
        )
        self.cases.append(case)
        self._save()
        log.info(f"Добавлен проблемный случай: {case_id}")
        return case_id

    def get_case(self, case_id: str) -> Optional[BadCase]:
        """Получает случай по ID."""
        for case in self.cases:
            if case.id == case_id:
                return case
        return None

    def list_cases(
        self,
        limit: int = 10,
        error_type: Optional[str] = None,
        unresolved_only: bool = False,
    ) -> list[BadCase]:
        """
        Возвращает список случаев с фильтрацией.

        :param limit: Максимальное количество случаев
        :param error_type: Фильтр по типу ошибки
        :param unresolved_only: Только нерешенные случаи
        """
        cases = self.cases
        if error_type:
            cases = [c for c in cases if c.error_type == error_type]
        if unresolved_only:
            cases = [c for c in cases if not c.resolved]
        return cases[-limit:]

    def mark_resolved(self, case_id: str, notes: str = "") -> bool:
        """Отмечает случай как решенный."""
        case = self.get_case(case_id)
        if case:
            case.resolved = True
            case.resolution_notes = notes
            self._save()
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику по проблемным случаям."""
        if not self.cases:
            return {"total": 0, "resolved": 0, "unresolved": 0, "by_type": {}}

        by_type: dict[str, int] = {}
        for case in self.cases:
            by_type[case.error_type] = by_type.get(case.error_type, 0) + 1

        return {
            "total": len(self.cases),
            "resolved": sum(1 for c in self.cases if c.resolved),
            "unresolved": sum(1 for c in self.cases if not c.resolved),
            "by_type": by_type,
        }


# Глобальный экземпляр
bad_case_manager = BadCaseManager()
