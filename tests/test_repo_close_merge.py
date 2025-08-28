import pytest
import subprocess
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from modules import repo
import json
import datetime

# Fixture for a temporary repository path
@pytest.fixture
def temp_repo_path(tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    # Initial commit
    (repo_dir / "README.md").write_text("Initial commit")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    return repo_dir

# Fixture for a remote repository
@pytest.fixture
def remote_repo(tmp_path):
    remote_dir = tmp_path / "remote_repo"
    remote_dir.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_dir, check=True)
    return remote_dir

# Fixture for a cloned repository with an agent branch
@pytest.fixture
def cloned_repo_with_agent_branch(tmp_path, remote_repo):
    # Clone the bare remote to create a working copy
    clone_dir = tmp_path / "cloned_repo"
    subprocess.run(["git", "clone", str(remote_repo), str(clone_dir)], check=True)

    # Initial commit on main in the cloned repo, then push to remote
    (clone_dir / "initial.txt").write_text("Initial content")
    subprocess.run(["git", "add", "."], cwd=clone_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit on main"], cwd=clone_dir, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=clone_dir, check=True)

    # Create agent branch
    agent_id = "test-agent"
    task_slug = "test-task"
    agent_branch = f"agent/{task_slug}"
    subprocess.run(["git", "checkout", "-b", agent_branch], cwd=clone_dir, check=True)

    # Make some changes on agent branch
    (clone_dir / "agent_file.txt").write_text("Agent specific changes")
    subprocess.run(["git", "add", "."], cwd=clone_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Agent work"], cwd=clone_dir, check=True)

    return clone_dir, agent_id, task_slug, agent_branch

# Mock for _update_runtime_registry to capture registry state
@pytest.fixture(autouse=True)
def mock_runtime_registry():
    with patch("modules.repo._update_runtime_registry") as mock_update:
        yield mock_update

@pytest.fixture(autouse=True)
def setup_registry_path(tmp_path):
    # Ensure REGISTRY_PATH points to a temporary file for tests
    original_registry_path = repo.REGISTRY_PATH
    repo.REGISTRY_PATH = tmp_path / "runtime_registry.json"
    yield
    repo.REGISTRY_PATH = original_registry_path

def _read_mock_registry_calls(mock_update):
    """Helper to return the raw call arguments list of the mock registry update."""
    return mock_update.call_args_list

class TestRepoCloseMerge:

    def test_close_without_merge_success(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch
        
        # Make a change to commit
        (repo_path / "new_file.txt").write_text("Some content")

        repo.close(
            path=str(repo_path),
            message="Test close without merge",
            agent_id=agent_id,
            task_id=task_slug,
            remote="origin",
            merge=False
        )

        # Verify repository is cleaned up
        assert not repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 2 # Initial close + final remove
        
        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"
        assert "commit_sha" in initial_close_call_args[2]
        assert initial_close_call_args[2]["branch"] == agent_branch
        assert "closed_at" in initial_close_call_args[2]
        assert "merged_into" not in initial_close_call_args[2]

        # Second call: remove
        remove_call_kwargs = registry_calls[1].kwargs
        assert remove_call_kwargs["remove"] is True

    def test_close_with_merge_fast_forward(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch

        # Ensure main branch has no new commits, so fast-forward is possible
        # (cloned_repo_with_agent_branch fixture already sets this up)

        # Make a change to commit
        (repo_path / "new_file_ff.txt").write_text("Fast-forward content")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        repo.close(
            path=str(repo_path),
            message="Test close with fast-forward merge",
            agent_id=agent_id,
            task_id=task_slug,
            remote="origin",
            merge=True,
            target_branch="main"
        )

        # Verify repository is cleaned up
        assert not repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 3 # Initial close + merged + final remove

        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"

        # Second call: merged status
        merged_call_args = registry_calls[1].args
        assert merged_call_args[0] == agent_id
        assert merged_call_args[1] == str(repo_path)
        assert merged_call_args[2]["status"] == "merged"
        assert merged_call_args[2]["merged_into"] == "main"
        assert "merge_commit_sha" in merged_call_args[2]

        # Third call: remove
        remove_call_kwargs = registry_calls[2].kwargs
        assert remove_call_kwargs["remove"] is True

        # Verify remote main branch has the changes
        temp_clone_dir = repo_path.parent / "temp_main_clone"
        subprocess.run(["git", "clone", str(repo_path.parent / "remote_repo"), str(temp_clone_dir)], check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_clone_dir, check=True)
        assert (temp_clone_dir / "new_file_ff.txt").exists()
        shutil.rmtree(temp_clone_dir)

    def test_close_with_merge_commit(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch

        # Make a divergent commit on main in the remote to force a merge commit
        remote_path = repo_path.parent / "remote_repo"
        temp_main_clone = repo_path.parent / "temp_main_clone_divergent"
        subprocess.run(["git", "clone", str(remote_path), str(temp_main_clone)], check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_main_clone, check=True)
        (temp_main_clone / "main_divergent.txt").write_text("Divergent change on main")
        subprocess.run(["git", "add", "."], cwd=temp_main_clone, check=True)
        subprocess.run(["git", "commit", "-m", "Divergent commit on main"], cwd=temp_main_clone, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=temp_main_clone, check=True)
        shutil.rmtree(temp_main_clone)

        # Make a change to commit on agent branch
        (repo_path / "new_file_merge.txt").write_text("Merge commit content")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        repo.close(
            path=str(repo_path),
            message="Test close with merge commit",
            agent_id=agent_id,
            task_id=task_slug,
            remote="origin",
            merge=True,
            target_branch="main"
        )

        # Verify repository is cleaned up
        assert not repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 3 # Initial close + merged + final remove

        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"

        # Second call: merged status
        merged_call_args = registry_calls[1].args
        assert merged_call_args[0] == agent_id
        assert merged_call_args[1] == str(repo_path)
        assert merged_call_args[2]["status"] == "merged"
        assert merged_call_args[2]["merged_into"] == "main"
        assert "merge_commit_sha" in merged_call_args[2]

        # Third call: remove
        remove_call_kwargs = registry_calls[2].kwargs
        assert remove_call_kwargs["remove"] is True

        # Verify remote main branch has the changes and a merge commit
        temp_clone_dir = repo_path.parent / "temp_main_clone_verify"
        subprocess.run(["git", "clone", str(remote_path), str(temp_clone_dir)], check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_clone_dir, check=True)
        assert (temp_clone_dir / "new_file_merge.txt").exists()
        assert (temp_clone_dir / "main_divergent.txt").exists()
        
        log_output = subprocess.run(
            ["git", "log", "--oneline", "--merges"],
            cwd=temp_clone_dir,
            capture_output=True,
            text=True,
            check=True
        ).stdout
        assert f"Merge branch 'agent/{task_slug}' into main" in log_output
        shutil.rmtree(temp_clone_dir)

    def test_close_with_merge_conflict(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch

        # Create a conflict on main in the remote
        remote_path = repo_path.parent / "remote_repo"
        temp_main_clone = repo_path.parent / "temp_main_clone_conflict"
        subprocess.run(["git", "clone", str(remote_path), str(temp_main_clone)], check=True)
        subprocess.run(["git", "checkout", "main"], cwd=temp_main_clone, check=True)
        (temp_main_clone / "agent_file.txt").write_text("Content on main")
        subprocess.run(["git", "add", "."], cwd=temp_main_clone, check=True)
        subprocess.run(["git", "commit", "-m", "Conflict commit on main"], cwd=temp_main_clone, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=temp_main_clone, check=True)
        shutil.rmtree(temp_main_clone)

        # Create a conflicting change on agent branch
        (repo_path / "agent_file.txt").write_text("Content on agent branch")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        
        with pytest.raises(RuntimeError, match="Merge conflict"):
            repo.close(
                path=str(repo_path),
                message="Test close with merge conflict",
                agent_id=agent_id,
                task_id=task_slug,
                remote="origin",
                merge=True,
                target_branch="main"
            )

        # Verify repository is NOT cleaned up
        assert repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 2 # Initial close + conflict

        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"

        # Second call: conflict status
        conflict_call_args = registry_calls[1].args
        assert conflict_call_args[0] == agent_id
        assert conflict_call_args[1] == str(repo_path)
        assert conflict_call_args[2]["status"] == "conflict"
        assert conflict_call_args[2]["merged_into"] is None
        assert conflict_call_args[2]["merge_commit_sha"] is None
        assert conflict_call_args[2]["conflict_files"] == ["agent_file.txt"]
        assert "failure_reason" in conflict_call_args[2]
        assert conflict_call_args[2]["merged"] is False

    def test_close_with_merge_protected_branch(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch

        # Make a change to commit
        (repo_path / "protected_file.txt").write_text("Protected branch content")

        with pytest.raises(RuntimeError, match="Target branch 'master' is protected. Merge aborted."):
            repo.close(
                path=str(repo_path),
                message="Test close with protected branch merge",
                agent_id=agent_id,
                task_id=task_slug,
                remote="origin",
                merge=True,
                target_branch="master" # This will trigger the simple protection check
            )

        # Verify repository is NOT cleaned up
        assert repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 2 # Initial close + blocked

        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"

        # Second call: blocked status
        blocked_call_args = registry_calls[1].args
        assert blocked_call_args[0] == agent_id
        assert blocked_call_args[1] == str(repo_path)
        assert blocked_call_args[2]["status"] == "blocked"
        assert blocked_call_args[2]["merged_into"] is None
        assert blocked_call_args[2]["merge_commit_sha"] is None
        assert blocked_call_args[2]["conflict_files"] is None
        assert "failure_reason" in blocked_call_args[2] and "protected" in blocked_call_args[2]["failure_reason"]
        assert blocked_call_args[2]["merged"] is False

    def test_close_with_push_failure(self, cloned_repo_with_agent_branch, mock_runtime_registry):
        repo_path, agent_id, task_slug, agent_branch = cloned_repo_with_agent_branch

        # Make a change to commit
        (repo_path / "push_failure_file.txt").write_text("Push failure content")

        # Mock the push to fail
        with patch("subprocess.run") as mock_run:
            # Set up the mock to fail on the push to main branch
            def mock_run_side_effect(*args, **kwargs):
                cmd = args[0] if args else []
                if "push" in cmd and "main" in cmd:
                    raise subprocess.CalledProcessError(1, "git push", stderr="Push denied")
                return MagicMock()
            
            mock_run.side_effect = mock_run_side_effect

            with pytest.raises(RuntimeError, match="Push to protected branch"):
                repo.close(
                    path=str(repo_path),
                    message="Test close with push failure",
                    agent_id=agent_id,
                    task_id=task_slug,
                    remote="origin",
                    merge=True,
                    target_branch="main"
                )

        # Verify repository is NOT cleaned up
        assert repo_path.exists()

        # Verify registry updates
        registry_calls = _read_mock_registry_calls(mock_runtime_registry)
        assert len(registry_calls) == 2 # Initial close + blocked

        # First call: initial close status
        initial_close_call_args = registry_calls[0].args
        assert initial_close_call_args[0] == agent_id
        assert initial_close_call_args[1] == str(repo_path)
        assert initial_close_call_args[2]["status"] == "closed"

        # Second call: blocked status
        blocked_call_args = registry_calls[1].args
        assert blocked_call_args[0] == agent_id
        assert blocked_call_args[1] == str(repo_path)
        assert blocked_call_args[2]["status"] == "blocked"
        assert blocked_call_args[2]["merged"] is False
        assert "failure_reason" in blocked_call_args[2]