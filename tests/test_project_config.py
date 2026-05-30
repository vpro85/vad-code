"""
Тесты для конфигурации проекта.
"""

import json
from pathlib import Path

import pytest

from vad_code.core.project_config import ProjectConfig, ProjectConfigManager


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Создает временную директорию для проекта."""
    root = tmp_path / "test_project"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def config_manager(temp_project_root: Path) -> ProjectConfigManager:
    """Создает экземпляр ProjectConfigManager."""
    return ProjectConfigManager(str(temp_project_root))


class TestProjectConfig:
    """Тесты для ProjectConfig."""

    def test_default_values(self):
        config = ProjectConfig()
        assert config.python_version == "3.11"
        assert config.test_framework == "pytest"
        assert config.code_style == "black"
        assert config.enable_multi_agent is True
        assert config.max_iterations == 50
        assert config.allowed_tools == []
        assert config.excluded_paths == []
        assert config.custom_instructions == ""

    def test_to_dict(self):
        config = ProjectConfig(name="test", description="test project")
        data = config.to_dict()
        assert data["name"] == "test"
        assert data["description"] == "test project"
        assert data["python_version"] == "3.11"

    def test_from_dict(self):
        data = {
            "name": "test",
            "description": "test project",
            "python_version": "3.12",
            "enable_multi_agent": False,
        }
        config = ProjectConfig.from_dict(data)
        assert config.name == "test"
        assert config.python_version == "3.12"
        assert config.enable_multi_agent is False

    def test_from_dict_ignores_unknown_fields(self):
        data = {
            "name": "test",
            "unknown_field": "should be ignored",
        }
        config = ProjectConfig.from_dict(data)
        assert config.name == "test"


class TestProjectConfigManager:
    """Тесты для ProjectConfigManager."""

    def test_init_no_config_file(self, config_manager: ProjectConfigManager):
        assert config_manager.config_file is None
        assert config_manager.config.name == ""

    def test_create_default(self, config_manager: ProjectConfigManager):
        config_manager.create_default()
        assert config_manager.config_file is not None
        assert config_manager.config_file.exists()
        assert config_manager.config.name == "test_project"

    def test_save_and_load(self, temp_project_root: Path):
        manager = ProjectConfigManager(str(temp_project_root))
        manager.config.name = "My Project"
        manager.config.description = "A test project"
        manager.save()

        manager2 = ProjectConfigManager(str(temp_project_root))
        assert manager2.config.name == "My Project"
        assert manager2.config.description == "A test project"

    def test_get_effective_config(self, config_manager: ProjectConfigManager):
        config_manager.config.name = "test"
        effective = config_manager.get_effective_config()
        assert effective["name"] == "test"
        assert "python_version" in effective

    def test_load_existing_config(self, temp_project_root: Path):
        config_file = temp_project_root / "vad-code.json"
        config_data = {
            "name": "Existing Project",
            "description": "Already exists",
            "python_version": "3.10",
        }
        config_file.write_text(json.dumps(config_data))

        manager = ProjectConfigManager(str(temp_project_root))
        assert manager.config.name == "Existing Project"
        assert manager.config.python_version == "3.10"

    def test_config_file_priority(self, temp_project_root: Path):
        primary = temp_project_root / "vad-code.json"
        secondary = temp_project_root / ".vad_code.json"

        primary.write_text(json.dumps({"name": "primary"}))
        secondary.write_text(json.dumps({"name": "secondary"}))

        manager = ProjectConfigManager(str(temp_project_root))
        assert manager.config.name == "primary"
