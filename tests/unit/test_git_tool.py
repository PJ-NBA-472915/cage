"""Tests for GitTool staging and commit behavior."""

import subprocess
from pathlib import Path

import pytest

from src.cage.git_tool import GitTool


@pytest.fixture()
def temp_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
    return repo_path


def write_file(repo_path: Path, relative_path: str, content: str) -> None:
    """Helper to write content to a file inside the repo."""
    target = repo_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_add_and_commit_new_file(temp_repo):
    """GitTool should stage and commit newly created files."""
    repo = temp_repo
    git_tool = GitTool(repo)

    write_file(repo, "notes.txt", "hello world")

    add_result = git_tool.add_files()
    assert add_result.success, add_result.error

    status = git_tool.get_status()
    assert "notes.txt" in status.data["staged_files"]

    commit_result = git_tool.commit("feat: add sample notes")
    assert commit_result.success, commit_result.error


def test_add_stages_deleted_files(temp_repo):
    """GitTool.add_files should stage deletions so commits succeed."""
    repo = temp_repo
    git_tool = GitTool(repo)

    write_file(repo, "notes.txt", "hello world")
    git_tool.add_files()
    git_tool.commit("feat: seed notes")

    (repo / "notes.txt").unlink()

    add_result = git_tool.add_files()
    assert add_result.success, add_result.error

    status = git_tool.get_status()
    assert "notes.txt" in status.data["staged_files"], status.data
    assert status.data["staged_files"] == ["notes.txt"]

    commit_result = git_tool.commit("feat: remove seed notes")
    assert commit_result.success, commit_result.error


def test_commit_auto_stages_changes(temp_repo):
    """Commit should stage pending changes when nothing is staged yet."""
    repo = temp_repo
    git_tool = GitTool(repo)

    write_file(repo, "notes.txt", "iteration 3")

    commit_result = git_tool.commit("feat: auto stage note")
    assert commit_result.success, commit_result.error

    log = git_tool.get_commit_info()
    assert log.success
    assert log.data["title"].endswith("auto stage note")
