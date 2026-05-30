"""
Тесты для проектной памяти.
"""

from pathlib import Path

import pytest

from vad_code.core.project_memory import ProjectMemory, ProjectMemoryEntry


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Создает временную директорию для проекта."""
    return tmp_path / "test_project"


@pytest.fixture
def memory(temp_project_root: Path) -> ProjectMemory:
    """Создает экземпляр ProjectMemory."""
    temp_project_root.mkdir(parents=True, exist_ok=True)
    return ProjectMemory(str(temp_project_root))


class TestProjectMemoryEntry:
    """Тесты для записи в памяти."""

    def test_create_entry(self):
        entry = ProjectMemoryEntry(
            key="test_key",
            value="test_value",
            category="fact",
            timestamp=123.45,
            confidence=0.9,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.category == "fact"
        assert entry.timestamp == 123.45
        assert entry.confidence == 0.9


class TestProjectMemory:
    """Тесты для ProjectMemory."""

    def test_init_creates_empty_memory(self, memory: ProjectMemory):
        assert len(memory.entries) == 0

    def test_add_entry(self, memory: ProjectMemory):
        memory.add(key="test_key", value="test_value", category="fact")
        assert "test_key" in memory.entries
        assert memory.entries["test_key"].value == "test_value"

    def test_get_entry(self, memory: ProjectMemory):
        memory.add(key="test_key", value="test_value", category="fact")
        entry = memory.get("test_key")
        assert entry is not None
        assert entry.value == "test_value"

    def test_get_missing_entry(self, memory: ProjectMemory):
        entry = memory.get("nonexistent")
        assert entry is None

    def test_search_finds_entries(self, memory: ProjectMemory):
        memory.add(key="key1", value="hello world", category="fact")
        memory.add(key="key2", value="goodbye world", category="fact")
        results = memory.search("world")
        assert len(results) == 2

    def test_search_case_insensitive(self, memory: ProjectMemory):
        memory.add(key="Key1", value="Hello World", category="fact")
        results = memory.search("hello")
        assert len(results) == 1

    def test_search_no_results(self, memory: ProjectMemory):
        memory.add(key="key1", value="hello", category="fact")
        results = memory.search("nonexistent")
        assert len(results) == 0

    def test_get_by_category(self, memory: ProjectMemory):
        memory.add(key="key1", value="val1", category="architecture")
        memory.add(key="key2", value="val2", category="convention")
        memory.add(key="key3", value="val3", category="architecture")
        results = memory.get_by_category("architecture")
        assert len(results) == 2

    def test_save_and_load(self, temp_project_root: Path):
        memory = ProjectMemory(str(temp_project_root))
        memory.add(key="test_key", value="test_value", category="fact")
        memory.save()

        # Создаем новый экземпляр и загружаем
        memory2 = ProjectMemory(str(temp_project_root))
        assert "test_key" in memory2.entries
        assert memory2.entries["test_key"].value == "test_value"

    def test_clear(self, memory: ProjectMemory):
        memory.add(key="key1", value="val1", category="fact")
        memory.add(key="key2", value="val2", category="fact")
        memory.clear()
        assert len(memory.entries) == 0

    def test_get_stats(self, memory: ProjectMemory):
        memory.add(key="key1", value="val1", category="architecture")
        memory.add(key="key2", value="val2", category="convention")
        memory.add(key="key3", value="val3", category="architecture")
        stats = memory.get_stats()
        assert stats["total_entries"] == 3
        assert stats["categories"]["architecture"] == 2
        assert stats["categories"]["convention"] == 1

    def test_get_context_prompt_empty(self, memory: ProjectMemory):
        prompt = memory.get_context_prompt()
        assert prompt == ""

    def test_get_context_prompt_with_entries(self, memory: ProjectMemory):
        memory.add(key="arch1", value="Микросервисная архитектура", category="architecture")
        memory.add(key="conv1", value="PEP 8", category="convention")
        prompt = memory.get_context_prompt()
        assert "Контекст проекта" in prompt
        assert "Микросервисная архитектура" in prompt
        assert "PEP 8" in prompt
