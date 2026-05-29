"""Специализированные агенты для различных задач."""

from typing import Any

from vad_code.core.multi_agent.base_agent import AgentCapability, BaseAgent
from vad_code.infrastructure.logger import log


class CodeReviewAgent(BaseAgent):
    """Агент для code review и анализа качества кода."""

    def _setup_capabilities(self) -> None:
        self.capabilities = [
            AgentCapability(
                name="code_review",
                description="Проверка кода на ошибки и лучшие практики",
                priority=0.95,
                keywords=[
                    "review", "ревью", "проверка", "код", "code",
                    "quality", "качество", "best practices", "антипаттерн",
                    "antipattern", "code smell", "запах кода",
                ],
            ),
            AgentCapability(
                name="complexity_analysis",
                description="Анализ сложности функций и модулей",
                priority=0.85,
                keywords=[
                    "complexity", "сложность", "cyclomatic", "цикломатический",
                    "refactor", "рефакторинг", "simplify", "упростить",
                ],
            ),
            AgentCapability(
                name="find_bugs",
                description="Поиск потенциальных багов",
                priority=0.9,
                keywords=[
                    "bug", "баг", "ошибка", "error", "issue",
                    "potential", "потенциальная", "race condition",
                    "memory leak", "утечка памяти",
                ],
            ),
        ]

    def get_system_prompt(self) -> str:
        return (
            "Ты - эксперт по code review с глубоким знанием Python и лучших практик.\n\n"
            "ТВОИ ЗАДАЧИ:\n"
            "- Находить баги и потенциальные проблемы в коде\n"
            "- Оценивать качество кода по следующим критериям:\n"
            "  1. Читаемость и понятность\n"
            "  2. Следование PEP 8 и conventions\n"
            "  3. Сложность (цикломатическая, когнитивная)\n"
            "  4. Безопасность\n"
            "  5. Производительность\n"
            "  6. Тестируемость\n\n"
            "ФОРМАТ ОТВЕТА:\n"
            "## Code Review Report\n\n"
            "### 🚨 Критические проблемы\n"
            "(если есть)\n\n"
            "### ⚠️ Предупреждения\n"
            "(если есть)\n\n"
            "### 💡 Рекомендации\n"
            "(если есть)\n\n"
            "### 📊 Оценка качества\n"
            "- Читаемость: X/10\n"
            "- Сложность: X/10\n"
            "- Безопасность: X/10\n"
            "- Итого: X/10\n\n"
            "### 🎯 Предложения по рефакторингу\n"
            "(конкретные примеры кода)\n"
        )

    async def handle_task(
        self, task: str, context: dict[str, Any] | None = None
    ) -> str:
        """Выполняет code review."""
        log.info("🔍 Code Review Agent обрабатывает: %s...", task[:50])

        file_content = ""
        if context and "file_content" in context:
            file_content = context["file_content"]
        elif context and "file_path" in context:
            # Читаем файл через executor
            file_content = await self.executor.execute(
                '{"tool": "read_file", "arguments": {"path": "' + context["file_path"] + '"}}'
            ) or ""

        if not file_content:
            return "❌ Не удалось получить содержимое файла для review."

        # Формируем запрос к LLM
        review_prompt = (
            f"Проведи детальный code review следующего кода:\n\n"
            f"```python\n{file_content}\n```\n\n"
            f"Задача пользователя: {task}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": review_prompt},
        ]

        result = await self.llm_client.complete_with_retry(
            messages, max_retries=2, base_delay=1.0
        )

        self.stats["total_tokens"] += self.tokenizer.count_tokens(result)
        return result


class TestingAgent(BaseAgent):
    """Агент для написания и запуска тестов."""

    __test__ = False  # Чтобы pytest не пытался собрать этот класс как тест

    def _setup_capabilities(self) -> None:
        self.capabilities = [
            AgentCapability(
                name="write_tests",
                description="Написание unit и integration тестов",
                priority=0.95,
                keywords=[
                    "test", "тест", "testing", "тестирование",
                    "unit test", "integration test", "pytest",
                    "mock", "stub", "fixture",
                ],
            ),
            AgentCapability(
                name="run_tests",
                description="Запуск и анализ результатов тестов",
                priority=0.9,
                keywords=[
                    "run tests", "запустить тесты", "pytest",
                    "coverage", "покрытие", "failed", "провален",
                ],
            ),
            AgentCapability(
                name="debug_tests",
                description="Отладка падающих тестов",
                priority=0.85,
                keywords=[
                    "debug", "отладка", "failing", "падающий",
                    "assertion error", "assertionerror",
                    "test failure", "сбой теста",
                ],
            ),
        ]

    def get_system_prompt(self) -> str:
        return (
            "Ты - эксперт по тестированию Python с глубоким знанием pytest.\n\n"
            "ТВОИ ЗАДАЧИ:\n"
            "- Писать качественные unit и integration тесты\n"
            "- Использовать pytest fixtures, parametrization, mocks\n"
            "- Обеспечивать высокое покрытие кода тестами\n"
            "- Отлаживать падающие тесты\n\n"
            "ПРАВИЛА:\n"
            "- Тесты должны быть изолированными и детерминированными\n"
            "- Используй arrange-act-assert паттерн\n"
            "- Покрывай edge cases\n"
            "- Добавляй описательные имена тестам\n"
            "- Используй fixtures для повторного использования\n"
        )

    async def handle_task(
        self, task: str, context: dict[str, Any] | None = None
    ) -> str:
        """Выполняет задачу тестирования."""
        log.info("🧪 Testing Agent обрабатывает: %s...", task[:50])

        # Определяем тип задачи
        task_lower = task.lower()

        if "run" in task_lower or "запусти" in task_lower:
            return await self._run_tests(context)
        elif "debug" in task_lower or "отлад" in task_lower:
            return await self._debug_tests(context)
        else:
            return await self._write_tests(task, context)

    async def _write_tests(
        self, task: str, context: dict[str, Any] | None
    ) -> str:
        """Генерирует тесты."""
        source_code = ""
        if context and "file_content" in context:
            source_code = context["file_content"]
        elif context and "file_path" in context:
            source_code = await self.executor.execute(
                '{"tool": "read_file", "arguments": {"path": "' + context["file_path"] + '"}}'
            ) or ""

        if not source_code:
            return "❌ Не удалось получить исходный код для тестирования."

        test_prompt = (
            f"Напиши comprehensive тесты для следующего кода:\n\n"
            f"```python\n{source_code}\n```\n\n"
            f"Требования: {task}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": test_prompt},
        ]

        result = await self.llm_client.complete_with_retry(
            messages, max_retries=2, base_delay=1.0
        )

        self.stats["total_tokens"] += self.tokenizer.count_tokens(result)
        return result

    async def _run_tests(self, context: dict[str, Any] | None) -> str:
        """Запускает тесты."""
        test_path = "tests/"
        if context and "test_path" in context:
            test_path = context["test_path"]

        result = await self.executor.execute(
            '{"tool": "run_tests", "arguments": {"path": "' + test_path + '"}}'
        )
        return result or "Тесты выполнены без вывода."

    async def _debug_tests(self, context: dict[str, Any] | None) -> str:
        """Отлаживает тесты."""
        test_output = ""
        if context and "test_output" in context:
            test_output = context["test_output"] or ""
        else:
            test_output = await self.executor.execute(
                '{"tool": "run_tests", "arguments": {"path": "tests/"}}'
            ) or ""

        debug_prompt = (
            f"Проанализируй результаты тестов и предложи исправления:\n\n"
            f"```\n{test_output}\n```"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": debug_prompt},
        ]

        result = await self.llm_client.complete_with_retry(
            messages, max_retries=2, base_delay=1.0
        )

        self.stats["total_tokens"] += self.tokenizer.count_tokens(result)
        return result


class DocumentationAgent(BaseAgent):
    """Агент для работы с документацией."""

    def _setup_capabilities(self) -> None:
        self.capabilities = [
            AgentCapability(
                name="generate_docstring",
                description="Генерация docstrings",
                priority=0.95,
                keywords=[
                    "docstring", "документация", "documentation",
                    "docs", "комментарий", "comment",
                    "describe", "описать", "explain", "объяснить",
                ],
            ),
            AgentCapability(
                name="update_readme",
                description="Обновление README и документации проекта",
                priority=0.85,
                keywords=[
                    "readme", "readme.md", "документация проекта",
                    "update docs", "обновить документацию",
                    "changelog", "изменения",
                ],
            ),
            AgentCapability(
                name="api_docs",
                description="Генерация API документации",
                priority=0.9,
                keywords=[
                    "api", "api docs", "api документация",
                    "endpoint", "маршрут", "rest",
                    "swagger", "openapi",
                ],
            ),
        ]

    def get_system_prompt(self) -> str:
        return (
            "Ты - эксперт по технической документации.\n\n"
            "ТВОИ ЗАДАЧИ:\n"
            "- Писать понятные и полезные docstrings\n"
            "- Создавать документацию для API\n"
            "- Обновлять README и другие документы проекта\n"
            "- Следовать Google/NumPy/PEP 257 стилям docstrings\n\n"
            "ПРАВИЛА:\n"
            "- Docstrings должны описывать что делает функция, а не как\n"
            "- Указывай типы аргументов и возвращаемых значений\n"
            "- Приводи примеры использования\n"
            "- Документируй исключения\n"
            "- Используй ясный и лаконичный язык\n"
        )

    async def handle_task(
        self, task: str, context: dict[str, Any] | None = None
    ) -> str:
        """Выполняет задачу документации."""
        log.info("📝 Documentation Agent обрабатывает: %s...", task[:50])

        source_code = ""
        if context and "file_content" in context:
            source_code = context["file_content"]
        elif context and "file_path" in context:
            source_code = await self.executor.execute(
                '{"tool": "read_file", "arguments": {"path": "' + context["file_path"] + '"}}'
            ) or ""

        if not source_code:
            return "❌ Не удалось получить содержимое для документации."

        doc_prompt = (
            f"Создай документацию для следующего кода:\n\n"
            f"```python\n{source_code}\n```\n\n"
            f"Задача: {task}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": doc_prompt},
        ]

        result = await self.llm_client.complete_with_retry(
            messages, max_retries=2, base_delay=1.0
        )

        self.stats["total_tokens"] += self.tokenizer.count_tokens(result)
        return result


class SecurityAgent(BaseAgent):
    """Агент для анализа безопасности кода."""

    def _setup_capabilities(self) -> None:
        self.capabilities = [
            AgentCapability(
                name="security_audit",
                description="Аудит безопасности кода",
                priority=0.98,
                keywords=[
                    "security", "безопасность", "audit", "аудит",
                    "vulnerability", "уязвимость", "cve",
                    "injection", "xss", "csrf",
                    "уязвимости", "безопасен", "secure",
                ],
            ),
            AgentCapability(
                name="dependency_check",
                description="Проверка зависимостей на уязвимости",
                priority=0.85,
                keywords=[
                    "dependency", "зависимость", "package",
                    "safety", "pip audit", "safety check",
                    "outdated", "устаревший",
                ],
            ),
            AgentCapability(
                name="secret_detection",
                description="Поиск секретов и чувствительных данных",
                priority=0.9,
                keywords=[
                    "secret", "секрет", "password", "пароль",
                    "api key", "ключ api", "token", "токен",
                    "credential", "учетные данные",
                    "leak", "утечка",
                ],
            ),
        ]

    def get_system_prompt(self) -> str:
        return (
            "Ты - эксперт по безопасности Python-приложений.\n\n"
            "ТВОИ ЗАДАЧИ:\n"
            "- Находить уязвимости в коде\n"
            "- Проверять на injection-атаки (SQL, command, template)\n"
            "- Искать утечки секретов\n"
            "- Оценивать безопасность зависимостей\n"
            "- Проверять на OWASP Top 10\n\n"
            "ФОРМАТ ОТВЕТА:\n"
            "## Security Audit Report\n\n"
            "### 🚨 Критические уязвимости\n"
            "(CVE, CVSS score если применимо)\n\n"
            "### ⚠️ Предупреждения\n\n"
            "### 💡 Рекомендации\n\n"
            "### 📊 Оценка безопасности\n"
            "- Score: X/10\n"
        )

    async def handle_task(
        self, task: str, context: dict[str, Any] | None = None
    ) -> str:
        """Выполняет аудит безопасности."""
        log.info("🔒 Security Agent обрабатывает: %s...", task[:50])

        source_code = ""
        if context and "file_content" in context:
            source_code = context["file_content"]
        elif context and "file_path" in context:
            source_code = await self.executor.execute(
                '{"tool": "read_file", "arguments": {"path": "' + context["file_path"] + '"}}'
            ) or ""

        if not source_code:
            return "❌ Не удалось получить содержимое для аудита."

        security_prompt = (
            f"Проведи аудит безопасности следующего кода:\n\n"
            f"```python\n{source_code}\n```\n\n"
            f"Задача: {task}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": security_prompt},
        ]

        result = await self.llm_client.complete_with_retry(
            messages, max_retries=2, base_delay=1.0
        )

        self.stats["total_tokens"] += self.tokenizer.count_tokens(result)
        return result
