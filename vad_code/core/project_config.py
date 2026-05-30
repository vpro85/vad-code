"""
Конфигурация проектов - vad-code.json
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from vad_code.infrastructure.logger import log


@dataclass
class ProjectConfig:
    """Конфигурация проекта."""

    name: str = ""
    description: str = ""
    python_version: str = "3.11"
    test_framework: str = "pytest"
    code_style: str = "black"
    enable_multi_agent: bool = True
    max_iterations: int = 50
    allowed_tools: list[str] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=list)
    custom_instructions: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в словарь."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        """Создает из словаря."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProjectConfigManager:
    """Управление конфигурацией проектов."""

    CONFIG_FILENAMES = ["vad-code.json", ".vad_code.json", "vad_code_config.json"]

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)
        self.config_file: Path | None = None
        self.config: ProjectConfig = ProjectConfig()
        self._find_and_load()

    def _find_and_load(self) -> None:
        """Ищет и загружает файл конфигурации."""
        for filename in self.CONFIG_FILENAMES:
            candidate = self.project_root / filename
            if candidate.exists():
                self.config_file = candidate
                self._load()
                return

    def _load(self) -> None:
        """Загружает конфигурацию."""
        if self.config_file and self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.config = ProjectConfig.from_dict(data)
                log.info(
                    "📋 Загружена конфигурация проекта: %s",
                    self.config_file.name,
                )
            except Exception as e:
                log.warning(
                    "⚠️ Не удалось загрузить конфигурацию: %s", e
                )

    def save(self) -> None:
        """Сохраняет конфигурацию."""
        if not self.config_file:
            self.config_file = self.project_root / "vad-code.json"

        try:
            self.config_file.write_text(
                json.dumps(self.config.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.info("💾 Конфигурация сохранена: %s", self.config_file)
        except Exception as e:
            log.error("❌ Не удалось сохранить конфигурацию: %s", e)

    def create_default(self) -> None:
        """Создает файл конфигурации по умолчанию."""
        self.config_file = self.project_root / "vad-code.json"
        self.config = ProjectConfig(
            name=self.project_root.name,
            description="Проект, управляемый vad-code",
        )
        self.save()

    def get_effective_config(self) -> dict[str, Any]:
        """Возвращает эффективную конфигурацию с учетом настроек по умолчанию."""
        return self.config.to_dict()
