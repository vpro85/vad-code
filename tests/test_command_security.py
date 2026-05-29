"""Тесты для модуля безопасности команд."""

import pytest

from vad_code.infrastructure.command_security import (
    CommandValidator,
    command_validator,
    ALLOWED_COMMANDS,
    BLACKLISTED_COMMANDS,
)


@pytest.fixture
def validator():
    """Создает экземпляр CommandValidator."""
    return CommandValidator(max_timeout=120)


def test_validate_safe_command(validator):
    """Проверяет допустимую команду."""
    is_safe, message = validator.validate("pytest tests/")
    assert is_safe is True
    assert "безопасна" in message


def test_validate_empty_command(validator):
    """Проверяет пустую команду."""
    is_safe, message = validator.validate("")
    assert is_safe is False
    assert "Пустая команда" in message


def test_validate_blacklisted_command(validator):
    """Проверяет команду из черного списка (без опасных паттернов)."""
    is_safe, message = validator.validate("chmod 755 file.txt")
    assert is_safe is False
    assert "запрещена" in message


def test_validate_dangerous_pattern_rm_rf(validator):
    """Проверяет обнаружение опасного паттерна rm -rf."""
    is_safe, message = validator.validate("rm -rf /tmp/test")
    assert is_safe is False
    assert "опасный паттерн" in message


def test_validate_dangerous_pattern_sudo(validator):
    """Проверяет обнаружение sudo."""
    is_safe, message = validator.validate("sudo apt update")
    assert is_safe is False
    assert "опасный паттерн" in message


def test_validate_dangerous_pattern_eval(validator):
    """Проверяет обнаружение eval."""
    is_safe, message = validator.validate("eval 'rm -rf /'")
    assert is_safe is False
    assert "опасный паттерн" in message


def test_validate_dangerous_pattern_subshell(validator):
    """Проверяет обнаружение подстановки команды $()."""
    is_safe, message = validator.validate("echo $(cat /etc/passwd)")
    assert is_safe is False
    assert "опасный паттерн" in message


def test_validate_not_in_whitelist(validator):
    """Проверяет команду, не входящую в белый список."""
    # Создаем валидатор с ограниченным белым списком
    limited_validator = CommandValidator(allowed_commands={"pytest", "git"})
    is_safe, message = limited_validator.validate("ls -la")
    assert is_safe is False
    assert "не в белом списке" in message


def test_validate_timeout_ok(validator):
    """Проверяет допустимый таймаут."""
    is_valid, message = validator.validate_timeout(60)
    assert is_valid is True


def test_validate_timeout_too_long(validator):
    """Проверяет слишком большой таймаут."""
    is_valid, message = validator.validate_timeout(200)
    assert is_valid is False
    assert "превышает максимум" in message


def test_validate_timeout_negative(validator):
    """Проверяет отрицательный таймаут."""
    is_valid, message = validator.validate_timeout(-10)
    assert is_valid is False
    assert "положительным" in message


def test_extract_base_command(validator):
    """Проверяет извлечение базовой команды."""
    assert validator._extract_base_command("pytest tests/") == "pytest"
    assert validator._extract_base_command("/usr/bin/python script.py") == "python"
    assert validator._extract_base_command("git status") == "git"


def test_allowed_commands_not_empty():
    """Проверяет, что белый список не пуст."""
    assert len(ALLOWED_COMMANDS) > 0
    assert "pytest" in ALLOWED_COMMANDS
    assert "git" in ALLOWED_COMMANDS


def test_blacklisted_commands_not_empty():
    """Проверяет, что черный список не пуст."""
    assert len(BLACKLISTED_COMMANDS) > 0
    assert "rm" in BLACKLISTED_COMMANDS
    assert "sudo" in BLACKLISTED_COMMANDS


def test_global_validator_exists():
    """Проверяет существование глобального валидатора."""
    assert command_validator is not None
    assert isinstance(command_validator, CommandValidator)
