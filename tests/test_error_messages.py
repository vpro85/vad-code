"""Тесты для модуля улучшенных сообщений об ошибках."""

from vad_code.infrastructure.error_messages import (
    ErrorMessages,
    error_messages,
    format_error,
    get_available_tools_message,
    get_permission_info_message,
    get_command_security_message,
)


def test_format_tool_not_found():
    """Проверяет форматирование ошибки 'инструмент не найден'."""
    msg = format_error(
        "tool_not_found",
        tool_name="unknown_tool",
        available_tools="read_file, write_file"
    )
    assert "❌" in msg
    assert "unknown_tool" in msg
    assert "💡" in msg
    assert "📝" in msg


def test_format_validation_error():
    """Проверяет форматирование ошибки валидации."""
    msg = format_error("validation_error", tool_name="read_file")
    assert "❌" in msg
    assert "Ошибка валидации" in msg
    assert "💡" in msg


def test_format_permission_denied():
    """Проверяет форматирование ошибки доступа."""
    msg = format_error(
        "permission_denied",
        tool_name="delete_file",
        risk_level="dangerous",
        allowed_levels=["read", "write"]
    )
    assert "❌" in msg
    assert "Доступ запрещен" in msg
    assert "dangerous" in msg
    assert "💡" in msg


def test_format_timeout_error():
    """Проверяет форматирование ошибки таймаута."""
    msg = format_error("timeout_error", tool_name="run_command", timeout=120)
    assert "❌" in msg
    assert "Превышено время" in msg
    assert "120" in msg
    assert "💡" in msg


def test_format_file_not_found():
    """Проверяет форматирование ошибки 'файл не найден'."""
    msg = format_error("file_not_found", file_path="/path/to/file.txt")
    assert "❌" in msg
    assert "Файл не найден" in msg
    assert "/path/to/file.txt" in msg
    assert "💡" in msg


def test_format_permission_error():
    """Проверяет форматирование ошибки доступа к файлу."""
    msg = format_error("permission_error", file_path="/root/secret.txt")
    assert "❌" in msg
    assert "Ошибка доступа" in msg
    assert "💡" in msg


def test_format_disk_full():
    """Проверяет форматирование ошибки 'нет места на диске'."""
    msg = format_error("disk_full")
    assert "❌" in msg
    assert "Недостаточно места" in msg
    assert "💡" in msg


def test_format_invalid_json():
    """Проверяет форматирование ошибки JSON."""
    msg = format_error("invalid_json")
    assert "❌" in msg
    assert "Ошибка парсинга JSON" in msg
    assert "💡" in msg


def test_format_command_forbidden():
    """Проверяет форматирование ошибки запрещенной команды."""
    msg = format_error("command_forbidden", command="rm -rf /")
    assert "❌" in msg
    assert "Команда запрещена" in msg
    assert "rm -rf /" in msg
    assert "💡" in msg


def test_format_dangerous_pattern():
    """Проверяет форматирование ошибки опасного паттерна."""
    msg = format_error("dangerous_pattern", pattern="sudo")
    assert "❌" in msg
    assert "Обнаружен опасный паттерн" in msg
    assert "sudo" in msg
    assert "💡" in msg


def test_format_unexpected_error():
    """Проверяет форматирование неожиданной ошибки."""
    msg = format_error(
        "unexpected_error",
        error_type_name="RuntimeError",
        error_message="Что-то пошло не так"
    )
    assert "❌" in msg
    assert "Неожиданная ошибка" in msg
    assert "RuntimeError" in msg
    assert "💡" in msg


def test_format_unknown_error_type():
    """Проверяет форматирование неизвестного типа ошибки."""
    msg = format_error("unknown_error", message="Тестовая ошибка", suggestion="Попробуйте снова")
    assert "❌" in msg
    assert "Тестовая ошибка" in msg
    assert "💡" in msg
    assert "Попробуйте снова" in msg


def test_format_error_without_kwargs():
    """Проверяет форматирование без дополнительных параметров."""
    msg = format_error("invalid_json")
    assert "❌" in msg
    assert "💡" in msg


def test_get_available_tools_message():
    """Проверяет генерацию сообщения о доступных инструментах."""
    tools = ["read_file", "write_file", "list_files"]
    msg = get_available_tools_message(tools)
    assert "📋" in msg
    assert "read_file" in msg
    assert "write_file" in msg
    assert "list_files" in msg


def test_get_available_tools_message_empty():
    """Проверяет сообщение при пустом списке инструментов."""
    msg = get_available_tools_message([])
    assert "Нет доступных инструментов" in msg


def test_get_permission_info_message():
    """Проверяет генерацию информации о разрешениях."""
    msg = get_permission_info_message(
        tool_name="delete_file",
        risk_level="dangerous",
        allowed_levels=["read", "write"]
    )
    assert "🔒" in msg
    assert "delete_file" in msg
    assert "dangerous" in msg
    assert "read" in msg
    assert "write" in msg


def test_get_permission_info_message_all_allowed():
    """Проверяет информацию о разрешениях когда все разрешены."""
    msg = get_permission_info_message(
        tool_name="read_file",
        risk_level="read",
        allowed_levels=[]
    )
    assert "🔒" in msg
    assert "все" in msg


def test_get_command_security_message():
    """Проверяет генерацию сообщения о безопасности команды."""
    msg = get_command_security_message(
        command="rm -rf /",
        reason="Опасный паттерн: rm -rf"
    )
    assert "🚫" in msg
    assert "rm -rf /" in msg
    assert "Опасный паттерн" in msg
    assert "pytest" in msg  # Упоминаются разрешенные команды
    assert "git" in msg


def test_error_messages_global_instance():
    """Проверяет глобальный экземпляр."""
    assert error_messages is not None
    msg = error_messages.format_error("invalid_json")
    assert "❌" in msg


def test_templates_not_empty():
    """Проверяет, что шаблоны не пустые."""
    assert len(ErrorMessages.TEMPLATES) > 0
    assert "tool_not_found" in ErrorMessages.TEMPLATES
    assert "validation_error" in ErrorMessages.TEMPLATES
    assert "permission_denied" in ErrorMessages.TEMPLATES
    assert "timeout_error" in ErrorMessages.TEMPLATES
    assert "file_not_found" in ErrorMessages.TEMPLATES
    assert "unexpected_error" in ErrorMessages.TEMPLATES
