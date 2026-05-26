import subprocess
from unittest.mock import patch

import pytest

from vad_code.tools.git_tools import GitTools


@pytest.fixture
def mock_settings(tmp_path):
    # Переопределяем корень проекта для FileSystemService
    with patch('vad_code.infrastructure.file_system.settings') as mock:
        mock.project_root = str(tmp_path)
        yield mock


@pytest.fixture
def git_repo(mock_settings, tmp_path):
    # Инициализируем git репозиторий в tmp_path
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    # Настраиваем пользователя (обязательно для коммитов)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), capture_output=True)
    return tmp_path


@pytest.fixture
def tools(mock_settings):
    return GitTools()


def test_git_status(tools, git_repo):
    # Начальный статус (пустой репозиторий)
    result = tools.git_status()
    assert "Команда выполнена успешно" in result or result == ""
    # Создаем файл и проверяем статус
    file = git_repo / "test.txt"
    file.write_text("hello")
    result = tools.git_status()
    assert "?? test.txt" in result


def test_git_add_commit(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("hello")
    # Добавляем файл
    add_res = tools.git_add(".")
    assert "Ошибка Git" not in add_res
    # Коммитим
    commit_res = tools.git_commit("Initial commit")
    assert "Ошибка Git" not in commit_res
    assert "Initial commit" in commit_res
    # Проверяем лог
    log_res = tools.git_log()
    assert "Initial commit" in log_res


def test_git_diff(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("version 1")
    subprocess.run(["git", "add", "test.txt"], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "v1"], cwd=str(git_repo), capture_output=True)
    # Изменяем файл
    file.write_text("version 2")
    diff_res = tools.git_diff()
    assert "-version 1" in diff_res
    assert "+version 2" in diff_res


def test_git_branch_checkout(tools, git_repo):
    # Сначала делаем начальный коммит, чтобы создать HEAD
    file = git_repo / "initial.txt"
    file.write_text("initial")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(git_repo), capture_output=True)
    # Создаем ветку
    branch_res = tools.git_branch("feature")
    assert "Ошибка Git" not in branch_res
    # Переключаемся на нее
    checkout_res = tools.git_checkout("feature")
    assert "Ошибка Git" not in checkout_res
    # Проверяем, что ветка действительно переключилась
    current_branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=str(git_repo), text=True
    ).strip()
    assert current_branch == "feature"


def test_git_show(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("content")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "show test"], cwd=str(git_repo), capture_output=True)
    # Получаем хэш последнего коммита
    log = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(git_repo), text=True).strip()

    show_res = tools.git_show(log)
    assert "show test" in show_res
    assert "content" in show_res


def test_git_stash(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("initial")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(git_repo), capture_output=True)
    # Вносим изменения и прячем их
    file.write_text("modified")
    tools.git_stash("push")

    status_res = tools.git_status()
    assert "test.txt" not in status_res  # Файл должен быть чистым
    # Возвращаем изменения
    tools.git_stash("pop")
    status_res = tools.git_status()
    assert "M test.txt" in status_res


def test_git_merge(tools, git_repo):
    # Main commit
    file1 = git_repo / "f1.txt"
    file1.write_text("main")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "main commit"], cwd=str(git_repo), capture_output=True)
    # Feature branch commit
    tools.git_branch("feat")
    tools.git_checkout("feat")
    file2 = git_repo / "f2.txt"
    file2.write_text("feature")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat commit"], cwd=str(git_repo), capture_output=True)
    # Merge back to main
    tools.git_checkout("master")  # или 'main' в зависимости от git версии, но init обычно делает master
    # Если git по умолчанию создал 'master', переключаемся на него.
    # В новых версиях может быть 'main'. Проверим текущую ветку.
    current_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(git_repo), text=True).strip()
    tools.git_checkout(current_branch)
    merge_res = tools.git_merge("feat")
    assert "Merge made by the 'recursive' strategy" in merge_res or "Fast-forward" in merge_res
    assert (git_repo / "f2.txt").exists()


def test_git_blame(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("line 1\nline 2")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "blame test"], cwd=str(git_repo), capture_output=True)

    blame_res = tools.git_blame("test.txt")
    assert "Ошибка Git" not in blame_res
    assert "blame test" in blame_res


def test_git_log_file(tools, git_repo):
    file = git_repo / "test.txt"
    file.write_text("v1")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "commit 1"], cwd=str(git_repo), capture_output=True)
    file.write_text("v2")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "commit 2"], cwd=str(git_repo), capture_output=True)

    log_res = tools.git_log_file("test.txt")
    assert "Ошибка Git" not in log_res
    assert "commit 1" in log_res
    assert "commit 2" in log_res
