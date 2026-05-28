"""Тесты для модуля bad_cases."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from vad_code.infrastructure.bad_cases import BadCaseManager, BadCase


@pytest.fixture
def temp_bad_cases_file():
    """Создает временный файл для тестирования."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("[]")
        temp_path = f.name
    return temp_path


@pytest.fixture
def manager(temp_bad_cases_file):
    """Создает менеджер с временным файлом."""
    with patch("vad_code.infrastructure.bad_cases.BAD_CASES_FILE", temp_bad_cases_file):
        mgr = BadCaseManager()
        yield mgr
    # Очистка после теста
    if os.path.exists(temp_bad_cases_file):
        os.unlink(temp_bad_cases_file)


class TestBadCase:
    """Тесты для класса BadCase."""

    def test_create_bad_case(self):
        """Проверяем создание экземпляра BadCase."""
        case = BadCase(
            id="test_case_1",
            timestamp="2024-01-01T00:00:00",
            user_input="test input",
            ai_response="test response",
            error_type="parse_error",
        )
        assert case.id == "test_case_1"
        assert case.resolved is False
        assert case.resolution_notes == ""

    def test_to_dict(self):
        """Проверяем сериализацию в словарь."""
        case = BadCase(
            id="test_case_1",
            timestamp="2024-01-01T00:00:00",
            user_input="test input",
            ai_response="test response",
            error_type="parse_error",
        )
        data = case.to_dict()
        assert data["id"] == "test_case_1"
        assert data["user_input"] == "test input"
        assert data["resolved"] is False

    def test_from_dict(self):
        """Проверяем десериализацию из словаря."""
        data = {
            "id": "test_case_1",
            "timestamp": "2024-01-01T00:00:00",
            "user_input": "test input",
            "ai_response": "test response",
            "error_type": "parse_error",
            "error_details": "",
            "context": {},
            "resolved": False,
            "resolution_notes": "",
        }
        case = BadCase.from_dict(data)
        assert case.id == "test_case_1"
        assert case.user_input == "test input"


class TestBadCaseManager:
    """Тесты для BadCaseManager."""

    def test_load_empty(self, manager):
        """Проверяем загрузку пустого файла."""
        assert len(manager.cases) == 0

    def test_load_with_data(self, temp_bad_cases_file):
        """Проверяем загрузку данных из файла."""
        test_data = [
            {
                "id": "case_1",
                "timestamp": "2024-01-01T00:00:00",
                "user_input": "test input",
                "ai_response": "test response",
                "error_type": "parse_error",
                "error_details": "",
                "context": {},
                "resolved": False,
                "resolution_notes": "",
            }
        ]
        with open(temp_bad_cases_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        with patch(
            "vad_code.infrastructure.bad_cases.BAD_CASES_FILE", temp_bad_cases_file
        ):
            mgr = BadCaseManager()
            assert len(mgr.cases) == 1
            assert mgr.cases[0].id == "case_1"

    def test_add_case(self, manager):
        """Проверяем добавление нового случая."""
        case_id = manager.add_case(
            user_input="test input",
            ai_response="test response",
            error_type="parse_error",
        )
        assert case_id.startswith("case_")
        assert len(manager.cases) == 1
        assert manager.cases[0].user_input == "test input"

    def test_add_case_saves_to_file(self, manager, temp_bad_cases_file):
        """Проверяем, что случай сохраняется в файл."""
        manager.add_case(
            user_input="test input",
            ai_response="test response",
            error_type="parse_error",
        )

        # Проверяем, что файл содержит данные
        with open(temp_bad_cases_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["user_input"] == "test input"

    def test_get_case(self, manager):
        """Проверяем получение случая по ID."""
        case_id = manager.add_case(
            user_input="test input",
            ai_response="test response",
            error_type="parse_error",
        )
        case = manager.get_case(case_id)
        assert case is not None
        assert case.id == case_id

    def test_get_case_not_found(self, manager):
        """Проверяем, что несуществующий случай возвращает None."""
        case = manager.get_case("nonexistent_case")
        assert case is None

    def test_list_cases(self, manager):
        """Проверяем список случаев."""
        manager.add_case("input1", "response1", "parse_error")
        manager.add_case("input2", "response2", "invalid_json")

        cases = manager.list_cases(limit=5)
        assert len(cases) == 2

    def test_list_cases_with_filter(self, manager):
        """Проверяем фильтрацию по типу ошибки."""
        manager.add_case("input1", "response1", "parse_error")
        manager.add_case("input2", "response2", "invalid_json")

        cases = manager.list_cases(error_type="parse_error")
        assert len(cases) == 1
        assert cases[0].error_type == "parse_error"

    def test_list_cases_unresolved_only(self, manager):
        """Проверяем фильтрацию только нерешенных случаев."""
        case_id1 = manager.add_case("input1", "response1", "parse_error")
        case_id2 = manager.add_case("input2", "response2", "invalid_json")
        manager.mark_resolved(case_id1, "Fixed")

        cases = manager.list_cases(unresolved_only=True)
        assert len(cases) == 1
        assert cases[0].id == case_id2

    def test_mark_resolved(self, manager):
        """Проверяем отметку случая как решенного."""
        case_id = manager.add_case("input1", "response1", "parse_error")
        success = manager.mark_resolved(case_id, "Fixed the issue")

        assert success is True
        case = manager.get_case(case_id)
        assert case.resolved is True
        assert case.resolution_notes == "Fixed the issue"

    def test_mark_resolved_not_found(self, manager):
        """Проверяем отметку несуществующего случая."""
        success = manager.mark_resolved("nonexistent_case")
        assert success is False

    def test_get_stats_empty(self, manager):
        """Проверяем статистику для пустого списка."""
        stats = manager.get_stats()
        assert stats["total"] == 0
        assert stats["resolved"] == 0
        assert stats["unresolved"] == 0

    def test_get_stats_with_data(self, manager):
        """Проверяем статистику с данными."""
        manager.add_case("input1", "response1", "parse_error")
        manager.add_case("input2", "response2", "invalid_json")
        case_id = manager.add_case("input3", "response3", "parse_error")
        manager.mark_resolved(case_id)

        stats = manager.get_stats()
        assert stats["total"] == 3
        assert stats["resolved"] == 1
        assert stats["unresolved"] == 2
        assert stats["by_type"]["parse_error"] == 2
        assert stats["by_type"]["invalid_json"] == 1

    def test_load_corrupted_file(self, temp_bad_cases_file):
        """Проверяем обработку поврежденного файла."""
        with open(temp_bad_cases_file, "w", encoding="utf-8") as f:
            f.write("invalid json")

        with patch(
            "vad_code.infrastructure.bad_cases.BAD_CASES_FILE", temp_bad_cases_file
        ):
            mgr = BadCaseManager()
            assert len(mgr.cases) == 0  # Должен создать пустой список
