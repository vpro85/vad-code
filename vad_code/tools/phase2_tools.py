"""
Инструменты Фазы 2: Расширение возможностей (v0.5.0).
"""
import ast
import os
import re
import subprocess
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any

from ..infrastructure.file_system import FileSystemService
from ..infrastructure.command_security import command_validator
from .permissions import register_tool, ToolRiskLevel
from .schemas import (
    UninstallPackageSchema,
    ListPackagesSchema,
    UpdatePackageSchema,
    RunLinterSchema,
    SearchAndReplaceSchema,
    FindDuplicatesSchema,
    AnalyzeComplexitySchema,
    FindCodeSmellsSchema,
    GenerateDocstringSchema,
    AnalyzeDependenciesSchema,
    FindUnusedImportsSchema,
    ListProcessesSchema,
    KillProcessSchema,
    RunBackgroundTaskSchema,
)


class Phase2Tools:
    """Инструменты для расширенных возможностей."""

    def __init__(self) -> None:
        self.fs = FileSystemService()

    # =========================================================================
    # Управление пакетами
    # =========================================================================

    @register_tool(
        "удаляет Python-пакет через pip",
        schema=UninstallPackageSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def uninstall_package(self, package: str) -> str:
        """Удаляет Python-пакет."""
        try:
            result = subprocess.run(
                ["pip", "uninstall", "-y", package],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.fs.root,
                check=False,
            )

            if result.returncode == 0:
                return f"Пакет '{package}' успешно удалён.\n{result.stdout}"

            output = f"Код выхода: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            return output

        except subprocess.TimeoutExpired:
            return "Ошибка: время удаления пакета истекло (таймаут 120с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при удалении пакета: {e}"

    @register_tool(
        "показывает список установленных Python-пакетов",
        schema=ListPackagesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def list_packages(self, filter_pattern: str = "", show_upgradable: bool = False) -> str:
        """Показывает список установленных пакетов."""
        try:
            args = ["pip", "list"]
            if show_upgradable:
                args.append("--outdated")

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.fs.root,
                check=False,
            )

            if result.returncode != 0:
                return f"Ошибка: {result.stderr}"

            output = result.stdout

            # Применяем фильтр
            if filter_pattern:
                lines = output.split("\n")
                filtered = [lines[0], lines[1]] if len(lines) > 1 else []  # заголовок
                pattern_lower = filter_pattern.lower()
                for line in lines[2:]:
                    if pattern_lower in line.lower():
                        filtered.append(line)
                output = "\n".join(filtered)

            # Ограничение размера вывода
            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except subprocess.TimeoutExpired:
            return "Ошибка: время выполнения истекло (таймаут 60с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при получении списка пакетов: {e}"

    @register_tool(
        "обновляет Python-пакеты через pip",
        schema=UpdatePackageSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def update_package(self, package: str = "", user_install: bool = False) -> str:
        """Обновляет один или все Python-пакеты."""
        try:
            args = ["pip", "install", "--upgrade"]
            if user_install:
                args.append("--user")

            if package:
                args.append(package)
            else:
                # Обновить все устаревшие пакеты
                args.append("--upgrade")
                # Получаем список устаревших
                outdated_result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=self.fs.root,
                    check=False,
                )
                if outdated_result.returncode != 0 or not outdated_result.stdout.strip():
                    return "Нет пакетов для обновления."

                import json
                try:
                    packages = json.loads(outdated_result.stdout)
                    if not packages:
                        return "Нет пакетов для обновления."
                    pkg_names = [p["name"] for p in packages]
                    args.extend(pkg_names)
                except json.JSONDecodeError:
                    return "Ошибка: не удалось распарсить список пакетов."

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.fs.root,
                check=False,
            )

            if result.returncode == 0:
                return f"Пакеты успешно обновлены.\n{result.stdout}"

            output = f"Код выхода: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            return output

        except subprocess.TimeoutExpired:
            return "Ошибка: время обновления истекло (таймаут 300с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при обновлении пакетов: {e}"

    # =========================================================================
    # Линтеры
    # =========================================================================

    @register_tool(
        "запускает линтер (pylint, flake8, mypy) для проверки кода",
        schema=RunLinterSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def run_linter(self, tool: str = "pylint", path: str = ".", args: str = "") -> str:
        """Запускает линтер для проверки кода."""
        if tool not in ("pylint", "flake8", "mypy"):
            return f"Ошибка: неизвестный линтер '{tool}'. Используйте: pylint, flake8, mypy"

        try:
            cmd_args = [tool]
            if args:
                import shlex
                cmd_args.extend(shlex.split(args))
            cmd_args.append(path)

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.fs.root,
                check=False,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            # Ограничение размера вывода
            max_size = command_validator.max_output_size
            if len(stdout) > max_size:
                stdout = stdout[:max_size] + "\n... [вывод обрезан]"
            if len(stderr) > max_size:
                stderr = stderr[:max_size] + "\n... [вывод обрезан]"

            output = f"Код выхода: {exit_code}\n"
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
            if stderr:
                output += f"STDERR:\n{stderr}\n"

            return output

        except FileNotFoundError:
            return f"Ошибка: линтер '{tool}' не установлен. Установите его через pip."
        except subprocess.TimeoutExpired:
            return f"Ошибка: время выполнения линтера истекло (таймаут 120с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при запуске линтера: {e}"

    # =========================================================================
    # Поиск и замена
    # =========================================================================

    @register_tool(
        "массовая замена текста по шаблону в файлах",
        schema=SearchAndReplaceSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def search_and_replace(
        self,
        search_pattern: str,
        replace_with: str,
        path: str = ".",
        file_glob: str = "*.py",
        dry_run: bool = True,
    ) -> str:
        """Массовая замена текста по шаблону."""
        try:
            # Компилируем regex
            try:
                pattern = re.compile(search_pattern)
            except re.error as e:
                return f"Ошибка в регулярном выражении: {e}"

            # Находим файлы
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            files = list(target_path.rglob(file_glob))
            if not files:
                return f"Не найдено файлов по шаблону '{file_glob}' в '{path}'."

            changes = []
            total_replacements = 0

            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    new_content, count = pattern.subn(replace_with, content)

                    if count > 0:
                        rel_path = file_path.relative_to(self.fs.root)
                        changes.append(f"  {rel_path}: {count} замен(а/ы)")
                        total_replacements += count

                        if not dry_run:
                            file_path.write_text(new_content, encoding="utf-8")

                except (UnicodeDecodeError, PermissionError) as e:
                    changes.append(f"  {file_path.relative_to(self.fs.root)}: ошибка - {e}")

            if not changes:
                return f"Не найдено совпадений для '{search_pattern}' в файлах '{file_glob}'."

            mode = "DRY RUN (файлы не изменены)" if dry_run else "Файлы изменены"
            return (
                f"[{mode}] Найдено {total_replacements} замен(а/ы) в {len(changes)} файл(ах):\n"
                + "\n".join(changes)
            )

        except Exception as e:
            return f"Ошибка при поиске и замене: {e}"

    @register_tool(
        "поиск дублирующегося кода в проекте",
        schema=FindDuplicatesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def find_duplicates(
        self,
        path: str = ".",
        min_lines: int = 5,
        file_glob: str = "*.py",
    ) -> str:
        """Поиск дублирующихся блоков кода."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            files = list(target_path.rglob(file_glob))
            if not files:
                return f"Не найдено файлов по шаблону '{file_glob}' в '{path}'."

            # Собираем блоки кода из всех файлов
            blocks: dict[str, list[tuple[str, int]]] = {}

            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.splitlines()
                    rel_path = str(file_path.relative_to(self.fs.root))

                    # Скользящее окно
                    for i in range(len(lines) - min_lines + 1):
                        block = "\n".join(lines[i:i + min_lines]).strip()
                        if not block or len(block) < 20:  # Пропускаем пустые/короткие
                            continue

                        block_hash = hashlib.md5(block.encode()).hexdigest()
                        if block_hash not in blocks:
                            blocks[block_hash] = []
                        blocks[block_hash].append((rel_path, i + 1))

                except (UnicodeDecodeError, PermissionError):
                    continue

            # Находим дубликаты
            duplicates = {k: v for k, v in blocks.items() if len(v) > 1}

            if not duplicates:
                return f"Дублирующихся блоков кода (>= {min_lines} строк) не найдено."

            output = f"Найдено {len(duplicates)} дублирующихся блоков:\n\n"
            for idx, (block_hash, locations) in enumerate(duplicates.items(), 1):
                output += f"Дубликат #{idx}:\n"
                for file_path, line_num in locations:
                    output += f"  - {file_path}:{line_num}\n"
                output += "\n"

            # Ограничение размера
            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except Exception as e:
            return f"Ошибка при поиске дубликатов: {e}"

    # =========================================================================
    # Анализ кода
    # =========================================================================

    @register_tool(
        "анализ сложности функций в коде",
        schema=AnalyzeComplexitySchema,
        risk_level=ToolRiskLevel.READ,
    )
    def analyze_complexity(self, path: str = ".", threshold: int = 10) -> str:
        """Анализ цикломатической сложности функций."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            results = []

            def _analyze_file(file_path: Path) -> None:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                except (SyntaxError, UnicodeDecodeError):
                    return

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_complexity(node)
                        if complexity >= threshold:
                            rel_path = file_path.relative_to(self.fs.root)
                            results.append({
                                "file": str(rel_path),
                                "function": node.name,
                                "line": node.lineno,
                                "complexity": complexity,
                            })

            if target_path.is_file():
                _analyze_file(target_path)
            else:
                for py_file in target_path.rglob("*.py"):
                    _analyze_file(py_file)

            if not results:
                return f"Функций со сложностью >= {threshold} не найдено."

            # Сортируем по сложности (убывание)
            results.sort(key=lambda x: x["complexity"], reverse=True)

            output = f"Функции со сложностью >= {threshold}:\n\n"
            for r in results:
                output += f"  {r['file']}:{r['line']} - {r['function']}() [сложность: {r['complexity']}]\n"

            return output

        except Exception as e:
            return f"Ошибка при анализе сложности: {e}"

    def _calculate_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Расчёт цикломатической сложности функции."""
        complexity = 1  # Базовая сложность

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                complexity += len(child.ifs)

        return complexity

    @register_tool(
        "поиск запахов кода (code smells)",
        schema=FindCodeSmellsSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def find_code_smells(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Поиск распространённых запахов кода."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            smells: list[str] = []

            for file_path in target_path.rglob(file_glob):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                rel_path = str(file_path.relative_to(self.fs.root))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Длинная функция (>50 строк)
                        end_line = getattr(node, "end_lineno", None)
                        if end_line:
                            func_length = end_line - node.lineno + 1
                            if func_length > 50:
                                smells.append(
                                    f"  {rel_path}:{node.lineno} - '{node.name}()' "
                                    f"слишком длинная ({func_length} строк)"
                                )

                        # Много аргументов (>5)
                        args = node.args
                        total_args = len(args.args) + len(args.kwonlyargs)
                        if total_args > 5:
                            smells.append(
                                f"  {rel_path}:{node.lineno} - '{node.name}()' "
                                f"слишком много аргументов ({total_args})"
                            )

                    if isinstance(node, ast.ClassDef):
                        # Большой класс (>20 методов)
                        methods = [
                            n for n in node.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        if len(methods) > 20:
                            smells.append(
                                f"  {rel_path}:{node.lineno} - класс '{node.name}' "
                                f"слишком большой ({len(methods)} методов)"
                            )

            if not smells:
                return "Запахов кода не найдено."

            output = f"Найдено {len(smells)} запахов кода:\n\n"
            output += "\n".join(smells)

            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except Exception as e:
            return f"Ошибка при поиске запахов кода: {e}"

    # =========================================================================
    # Генерация документации
    # =========================================================================

    @register_tool(
        "генерация docstring для функций/классов",
        schema=GenerateDocstringSchema,
        risk_level=ToolRiskLevel.WRITE,
    )
    def generate_docstring(
        self,
        path: str,
        function_name: str = "",
        style: str = "google",
    ) -> str:
        """Генерация docstring для функций и классов."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists() or not target_path.is_file():
                return f"Ошибка: файл '{path}' не найден."

            content = target_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            changes_made = 0
            lines = content.splitlines(keepends=True)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if function_name and node.name != function_name:
                        continue

                    # Проверяем, есть ли уже docstring
                    has_docstring = (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                    )

                    if has_docstring:
                        continue

                    # Генерируем docstring
                    docstring = self._generate_docstring_text(node, style)

                    # Вставляем docstring после строки определения
                    insert_line = node.lineno  # 1-based
                    indent = " " * (node.col_offset)

                    docstring_lines = docstring.split("\n")
                    new_lines = [f"{indent}'''\n"]
                    for dl in docstring_lines:
                        new_lines.append(f"{indent}{dl}\n")
                    new_lines.append(f"{indent}'''\n")

                    lines[insert_line:insert_line] = new_lines
                    changes_made += 1

            if changes_made == 0:
                if function_name:
                    return f"Функция/класс '{function_name}' не найдена или уже имеет docstring."
                return "Все функции/классы уже имеют docstring."

            # Записываем обратно
            target_path.write_text("".join(lines), encoding="utf-8")
            return f"Сгенерировано {changes_made} docstring(ов) в файле '{path}'."

        except Exception as e:
            return f"Ошибка при генерации docstring: {e}"

    def _generate_docstring_text(self, node: ast.AST, style: str) -> str:
        """Генерация текста docstring."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            arg_names = [a.arg for a in args.args if a.arg != "self" and a.arg != "cls"]

            if style == "google":
                doc = f"{node.name}.\n\nArgs:\n"
                for arg in arg_names:
                    doc += f"    {arg}: Описание аргумента.\n"
                if not arg_names:
                    doc = f"{node.name}."
                return doc.strip()

            elif style == "numpy":
                doc = f"{node.name}.\n\nParameters\n----------\n"
                for arg in arg_names:
                    doc += f"{arg} : type\n    Описание аргумента.\n"
                if not arg_names:
                    doc = f"{node.name}."
                return doc.strip()

            elif style == "sphinx":
                doc = f"{node.name}.\n\n"
                for arg in arg_names:
                    doc += f":param {arg}: Описание аргумента.\n"
                if not arg_names:
                    doc = f"{node.name}."
                return doc.strip()

        elif isinstance(node, ast.ClassDef):
            return f"Класс {node.name}."

        return "Описание."

    # =========================================================================
    # Анализ зависимостей
    # =========================================================================

    @register_tool(
        "анализ графа зависимостей проекта",
        schema=AnalyzeDependenciesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def analyze_dependencies(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Анализ зависимостей между модулями."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            dependencies: dict[str, set[str]] = {}

            for file_path in target_path.rglob(file_glob):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                rel_path = str(file_path.relative_to(self.fs.root))
                imports: set[str] = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])

                dependencies[rel_path] = imports

            if not dependencies:
                return "Не найдено файлов для анализа."

            output = "Граф зависимостей:\n\n"
            for file_path, deps in sorted(dependencies.items()):
                if deps:
                    output += f"  {file_path}:\n"
                    for dep in sorted(deps):
                        output += f"    -> {dep}\n"
                else:
                    output += f"  {file_path}: (нет импортов)\n"

            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except Exception as e:
            return f"Ошибка при анализе зависимостей: {e}"

    @register_tool(
        "поиск неиспользуемых импортов",
        schema=FindUnusedImportsSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def find_unused_imports(self, path: str = ".", file_glob: str = "*.py") -> str:
        """Поиск неиспользуемых импортов в файлах."""
        try:
            target_path = self.fs.safe_path(path)
            if not target_path.exists():
                return f"Ошибка: путь '{path}' не существует."

            unused: list[str] = []

            for file_path in target_path.rglob(file_glob):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                rel_path = str(file_path.relative_to(self.fs.root))

                # Собираем все импорты
                imported_names: list[tuple[str, int]] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            imported_names.append((name, node.lineno))
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            imported_names.append((name, node.lineno))

                # Проверяем использование
                for name, line_num in imported_names:
                    # Ищем имя в остальном коде (кроме импортов)
                    used = False
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            continue
                        if isinstance(node, ast.Name) and node.id == name:
                            used = True
                            break
                        if isinstance(node, ast.Attribute):
                            if isinstance(node.value, ast.Name) and node.value.id == name:
                                used = True
                                break

                    if not used:
                        unused.append(f"  {rel_path}:{line_num} - '{name}'")

            if not unused:
                return "Неиспользуемых импортов не найдено."

            output = f"Найдено {len(unused)} неиспользуемых импортов:\n\n"
            output += "\n".join(unused)

            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except Exception as e:
            return f"Ошибка при поиске неиспользуемых импортов: {e}"

    # =========================================================================
    # Работа с процессами
    # =========================================================================

    @register_tool(
        "показывает список процессов",
        schema=ListProcessesSchema,
        risk_level=ToolRiskLevel.READ,
    )
    def list_processes(self, filter_pattern: str = "") -> str:
        """Показывает список активных процессов."""
        try:
            import platform
            system = platform.system()

            if system == "Windows":
                cmd = ["tasklist", "/FO", "CSV"]
            else:
                cmd = ["ps", "aux"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                return f"Ошибка: {result.stderr}"

            output = result.stdout

            # Применяем фильтр
            if filter_pattern:
                lines = output.split("\n")
                filtered = [lines[0]] if lines else []  # заголовок
                pattern_lower = filter_pattern.lower()
                for line in lines[1:]:
                    if pattern_lower in line.lower():
                        filtered.append(line)
                output = "\n".join(filtered)

            max_size = command_validator.max_output_size
            if len(output) > max_size:
                output = output[:max_size] + "\n... [вывод обрезан]"

            return output

        except subprocess.TimeoutExpired:
            return "Ошибка: время выполнения истекло (таймаут 30с)."
        except (OSError, ValueError) as e:
            return f"Ошибка при получении списка процессов: {e}"

    @register_tool(
        "завершает процесс по PID",
        schema=KillProcessSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def kill_process(self, pid: int, force: bool = False) -> str:
        """Завершает процесс по PID."""
        try:
            import platform
            import signal
            import os

            system = platform.system()

            if system == "Windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1, False, pid)
                if handle == 0:
                    return f"Ошибка: процесс с PID {pid} не найден."
                if force:
                    kernel32.TerminateProcess(handle, 0)
                else:
                    kernel32.GenerateConsoleCtrlEvent(0, pid)
                kernel32.CloseHandle(handle)
            else:
                sig = signal.SIGKILL if force else signal.SIGTERM
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    return f"Ошибка: процесс с PID {pid} не найден."
                except PermissionError:
                    return f"Ошибка: нет прав для завершения процесса {pid}."

            return f"Процесс {pid} успешно завершён {'(принудительно)' if force else ''}."

        except Exception as e:
            return f"Ошибка при завершении процесса: {e}"

    @register_tool(
        "запускает команду в фоне",
        schema=RunBackgroundTaskSchema,
        risk_level=ToolRiskLevel.DANGEROUS,
    )
    def run_background_task(self, command: str, timeout: int = 300) -> str:
        """Запускает команду в фоновом режиме."""
        # Проверка безопасности
        is_safe, message = command_validator.validate(command)
        if not is_safe:
            return f"Ошибка безопасности: {message}"

        try:
            import shlex
            args = shlex.split(command)

            # Запускаем в отдельном потоке
            future: Future[str] = Future()

            def _run() -> str:
                try:
                    result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=self.fs.root,
                        check=False,
                    )
                    output = f"Код выхода: {result.returncode}\n"
                    if result.stdout:
                        output += f"STDOUT:\n{result.stdout}\n"
                    if result.stderr:
                        output += f"STDERR:\n{result.stderr}\n"
                    return output
                except subprocess.TimeoutExpired:
                    return f"Ошибка: время выполнения истекло (таймаут {timeout}с)."
                except Exception as e:
                    return f"Ошибка: {e}"

            thread = ThreadPoolExecutor(max_workers=1)
            future = thread.submit(_run)

            return (
                f"Фоновая задача запущена: '{command}'\n"
                f"Таймаут: {timeout}с\n"
                f"Для получения результата используйте run_command с проверкой статуса."
            )

        except (OSError, ValueError) as e:
            return f"Ошибка при запуске фоновой задачи: {e}"


# Автоматическая регистрация при импорте
_phase2_tools_instance = Phase2Tools()


def _register_phase2_tools() -> None:
    """Регистрация инструментов Фазы 2."""
    pass  # Инструменты регистрируются через декоратор @register_tool


_register_phase2_tools()
