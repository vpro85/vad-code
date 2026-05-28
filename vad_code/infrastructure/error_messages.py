"""
Модуль улучшенных сообщений об ошибках.
Предоставляет понятные и дружелюбные сообщения с рекомендациями.
"""


class ErrorMessages:
    """Генератор улучшенных сообщений об ошибках."""

    # Шаблоны сообщений об ошибках
    TEMPLATES = {
        "tool_not_found": {
            "message": "Инструмент '{tool_name}' не найден",
            "suggestion": "Проверьте имя инструмента. Доступные инструменты: {available_tools}",
            "example": 'Пример: {{"tool": "read_file", "arguments": {{"path": "file.txt"}}}}',
        },
        "validation_error": {
            "message": "Ошибка валидации аргументов",
            "suggestion": "Проверьте типы и обязательные поля. Используйте schema для проверки.",
            "example": 'Пример: {{"tool": "read_file", "arguments": {{"path": "file.txt"}}}}',
        },
        "permission_denied": {
            "message": "Доступ запрещен",
            "suggestion": (
                "Инструмент '{tool_name}' требует уровень риска "
                "'{risk_level}', но разрешены только: {allowed_levels}"
            ),
            "example": "Измените ALLOWED_TOOL_RISK_LEVELS в .env или используйте --permissions",
        },
        "timeout_error": {
            "message": "Превышено время выполнения",
            "suggestion": (
                "Инструмент '{tool_name}' выполнялся дольше {timeout}с. "
                "Попробуйте уменьшить объем данных или увеличить таймаут."
            ),
            "example": "Увеличьте TIMEOUT в .env (сейчас: {timeout}с)",
        },
        "file_not_found": {
            "message": "Файл не найден: {file_path}",
            "suggestion": "Проверьте путь к файлу. Используйте list_files или list_tree для просмотра структуры.",
            "example": 'Пример: {{"tool": "list_files", "arguments": {{"path": "."}}}}',
        },
        "permission_error": {
            "message": "Ошибка доступа к файлу: {file_path}",
            "suggestion": "Проверьте права доступа к файлу. Возможно, файл заблокирован или требует root-прав.",
            "example": "Проверьте права: ls -la {file_path}",
        },
        "disk_full": {
            "message": "Недостаточно места на диске",
            "suggestion": "Освободите место на диске или используйте другой путь для сохранения.",
            "example": "Проверьте свободное место: df -h",
        },
        "invalid_json": {
            "message": "Ошибка парсинга JSON",
            "suggestion": "Проверьте формат JSON. Убедитесь, что все строки экранированы и скобки закрыты.",
            "example": 'Пример: {{"tool": "read_file", "arguments": {{"path": "file.txt"}}}}',
        },
        "command_forbidden": {
            "message": "Команда запрещена: {command}",
            "suggestion": "Эта команда находится в черном списке безопасности. Используйте разрешенные команды.",
            "example": "Разрешенные команды: pytest, git, python, ls, cat, grep и др.",
        },
        "dangerous_pattern": {
            "message": "Обнаружен опасный паттерн: {pattern}",
            "suggestion": "Этот паттерн может быть опасен для системы. Избегайте его использования.",
            "example": "Используйте безопасные альтернативы.",
        },
        "unexpected_error": {
            "message": "Неожиданная ошибка",
            "suggestion": "Произошла непредвиденная ошибка. Проверьте логи для деталей.",
            "example": "Тип ошибки: {error_type_name}, Сообщение: {error_message}",
        },
    }

    @classmethod
    def format_error(cls, error_type: str, **kwargs: object) -> str:
        """
        Форматирует сообщение об ошибке с рекомендациями.

        :param error_type: Тип ошибки (ключ из TEMPLATES)
        :param kwargs: Дополнительные параметры для подстановки
        :return: Форматированное сообщение об ошибке
        """
        template = cls.TEMPLATES.get(error_type)
        if not template:
            return cls._format_generic_error(error_type, **kwargs)

        lines = []

        # Основное сообщение
        message = (
            template["message"].format(**kwargs) if kwargs else template["message"]
        )
        lines.append(f"❌ {message}")

        # Рекомендация
        suggestion = (
            template["suggestion"].format(**kwargs)
            if kwargs
            else template["suggestion"]
        )
        lines.append(f"💡 {suggestion}")

        # Пример (если есть)
        if "example" in template:
            example = (
                template["example"].format(**kwargs) if kwargs else template["example"]
            )
            lines.append(f"📝 {example}")

        return "\n".join(lines)

    @classmethod
    def _format_generic_error(cls, error_type: str, **kwargs) -> str:
        """Форматирует ошибку без шаблона."""
        message = kwargs.get("message", "Произошла ошибка")
        suggestion = kwargs.get("suggestion", "Проверьте параметры и попробуйте снова.")

        lines = [
            f"❌ {message}",
            f"💡 {suggestion}",
        ]

        if kwargs.get("example"):
            lines.append(f"📝 {kwargs['example']}")

        return "\n".join(lines)

    @classmethod
    def get_available_tools_message(cls, available_tools: list[str]) -> str:
        """Генерирует сообщение со списком доступных инструментов."""
        if not available_tools:
            return "Нет доступных инструментов."

        lines = ["📋 Доступные инструменты:"]
        for i, tool in enumerate(sorted(available_tools), 1):
            lines.append(f"  {i}. {tool}")

        return "\n".join(lines)

    @classmethod
    def get_permission_info_message(
        cls, tool_name: str, risk_level: str, allowed_levels: list[str]
    ) -> str:
        """Генерирует сообщение об информации о разрешениях."""
        lines = [
            f"🔒 Инструмент '{tool_name}' требует уровень риска: {risk_level}",
            f"   Разрешены уровни: {', '.join(allowed_levels) if allowed_levels else 'все'}",
            "",
            "   Уровни риска:",
            "   - READ: чтение файлов, просмотр структуры (безопасно)",
            "   - WRITE: запись файлов, создание директорий (изменяет файлы)",
            "   - DANGEROUS: удаление файлов, выполнение команд (требует осторожности)",
            "",
            "   Для изменения разрешений отредактируйте ALLOWED_TOOL_RISK_LEVELS в .env",
        ]
        return "\n".join(lines)

    @classmethod
    def get_command_security_message(cls, command: str, reason: str) -> str:
        """Генерирует сообщение о безопасности команды."""
        lines = [
            f"🚫 Команда '{command}' заблокирована системой безопасности",
            f"   Причина: {reason}",
            "",
            "   Для безопасности разрешены только проверенные команды:",
            "   - Тестирование: pytest, unittest, coverage",
            "   - Линтеры: pylint, flake8, mypy, ruff, black, isort",
            "   - Git: git",
            "   - Python: python, python3, pip, pip3",
            "   - Утилиты: ls, cat, head, tail, grep, find, wc, du, df, tree",
            "   - Сетевые: curl, wget",
            "   - Сборка: make, cmake, npm, yarn",
            "   - Docker: docker, docker-compose",
            "",
            "   Запрещены опасные команды: rm, sudo, chmod, mkfs, dd и др.",
        ]
        return "\n".join(lines)


# Глобальный экземпляр для удобства использования
error_messages = ErrorMessages()


def format_error(error_type: str, **kwargs: object) -> str:
    """Удобная функция для форматирования ошибок."""
    return error_messages.format_error(error_type, **kwargs)


def get_available_tools_message(available_tools: list[str]) -> str:
    """Удобная функция для получения сообщения о доступных инструментах."""
    return error_messages.get_available_tools_message(available_tools)


def get_permission_info_message(
    tool_name: str, risk_level: str, allowed_levels: list[str]
) -> str:
    """Удобная функция для получения информации о разрешениях."""
    return error_messages.get_permission_info_message(
        tool_name, risk_level, allowed_levels
    )


def get_command_security_message(command: str, reason: str) -> str:
    """Удобная функция для получения сообщения о безопасности команды."""
    return error_messages.get_command_security_message(command, reason)
