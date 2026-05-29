"""
Инструменты для управления проблемными случаями.
"""

from ..infrastructure.bad_cases import bad_case_manager
from .permissions import register_tool
from .schemas import (
    ReportBadCaseSchema,
    ListBadCasesSchema,
    GetBadCaseSchema,
    MarkBadCaseResolvedSchema,
)


class BadCaseTools:
    """Инструменты для работы с проблемными случаями распознавания команд."""

    @register_tool(
        "регистрирует проблемный случай распознавания команды для последующего анализа",
        schema=ReportBadCaseSchema,
    )
    def report_bad_case(
        self,
        user_input: str,
        ai_response: str,
        error_type: str,
        error_details: str = "",
    ) -> str:
        """Регистрирует проблемный случай."""
        try:
            case_id = bad_case_manager.add_case(
                user_input=user_input,
                ai_response=ai_response,
                error_type=error_type,
                error_details=error_details,
            )
            return (
                f"Проблемный случай зарегистрирован: {case_id}. "
                f"Теперь вы можете изучить его с помощью get_bad_case."
            )
        except Exception as e:
            return f"Ошибка при регистрации случая: {e}"

    @register_tool(
        "показывает список проблемных случаев распознавания команд",
        schema=ListBadCasesSchema,
    )
    def list_bad_cases(self, limit: int = 10, unresolved_only: bool = False) -> str:
        """Возвращает список проблемных случаев."""
        try:
            cases = bad_case_manager.list_cases(
                limit=limit, unresolved_only=unresolved_only
            )
            if not cases:
                return "Проблемных случаев не найдено."

            lines = [f"Найдено {len(cases)} случаев:"]
            for case in cases:
                status = "✅ Решен" if case.resolved else "❌ Не решен"
                lines.append(
                    f"- [{status}] {case.id} | {case.error_type} | "
                    f"{case.timestamp[:19]} | "
                    f"Запрос: {case.user_input[:50]}..."
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении списка: {e}"

    @register_tool(
        "показывает детали конкретного проблемного случая",
        schema=GetBadCaseSchema,
    )
    def get_bad_case(self, case_id: str) -> str:
        """Возвращает детали случая."""
        try:
            case = bad_case_manager.get_case(case_id)
            if not case:
                return f"Случай {case_id} не найден."

            status = "✅ Решен" if case.resolved else "❌ Не решен"
            lines = [
                f"ID: {case.id}",
                f"Статус: {status}",
                f"Время: {case.timestamp}",
                f"Тип ошибки: {case.error_type}",
                f"Детали: {case.error_details}",
                "---",
                f"Запрос пользователя:\n{case.user_input}",
                "---",
                f"Ответ AI:\n{case.ai_response}",
            ]
            if case.resolved and case.resolution_notes:
                lines.extend(["---", f"Решение:\n{case.resolution_notes}"])
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении деталей: {e}"

    @register_tool(
        "отмечает проблемный случай как решенный",
        schema=MarkBadCaseResolvedSchema,
    )
    def mark_bad_case_resolved(self, case_id: str, notes: str = "") -> str:
        """Отмечает случай как решенный."""
        try:
            success = bad_case_manager.mark_resolved(case_id, notes)
            if success:
                return f"Случай {case_id} отмечен как решенный."
            return f"Случай {case_id} не найден."
        except Exception as e:
            return f"Ошибка при отметке: {e}"

    @register_tool(
        "показывает статистику по проблемным случаям",
    )
    def get_bad_cases_stats(self) -> str:
        """Возвращает статистику по проблемным случаям."""
        try:
            stats = bad_case_manager.get_stats()
            lines = [
                "Статистика проблемных случаев:",
                f"- Всего: {stats['total']}",
                f"- Решено: {stats['resolved']}",
                f"- Не решено: {stats['unresolved']}",
                "- По типам:",
            ]
            for error_type, count in stats.get("by_type", {}).items():
                lines.append(f"  - {error_type}: {count}")
            return "\n".join(lines)
        except Exception as e:
            return f"Ошибка при получении статистики: {e}"
