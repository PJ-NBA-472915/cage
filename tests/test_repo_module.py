
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from modules import repo

class TestRepoModule(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.test_dir) / "coordination" / "runtime_registry.json"
        self.registry_path.parent.mkdir()
        # ToDo: monkeypatch the path to coordination/runtime_registry.json
        # For now, we'll just create it in the test directory
        repo.REGISTRY_PATH = self.registry_path


    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_init_with_local_path_directory(self):
        """Test initialising from a local directory."""
        local_repo = Path(self.test_dir) / "local_repo"
        local_repo.mkdir()
        (local_repo / "test.txt").write_text("hello")

        metadata = repo.init(origin=str(local_repo))
        
        self.assertTrue(Path(metadata["temp_dir"]).exists())
        self.assertTrue((Path(metadata["temp_dir"]) / "test.txt").exists())
        self.assertFalse(metadata["is_remote"])
        self.assertIsNone(metadata["commit"])

    def test_init_with_local_git_repo_captures_head(self):
        """Test initialising from a local git repo and capturing HEAD."""
        local_repo = Path(self.test_dir) / "local_git_repo"
        local_repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(local_repo), check=True)
        (local_repo / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=str(local_repo), check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=str(local_repo), check=True)
        
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(local_repo),
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()

        metadata = repo.init(origin=str(local_repo))
        
        self.assertEqual(metadata["commit"], head_commit)
        self.assertTrue((Path(metadata["temp_dir"]) / ".git").exists())

    @patch("modules.repo._clone_remote")
    def test_init_with_remote_url_shallow_clone(self, mock_clone_remote):
        """Test that a shallow clone is performed for remote URLs."""
        remote_url = "https://github.com/test/repo.git"
        repo.init(origin=remote_url, shallow=True)
        
        mock_clone_remote.assert_called_once()
        args, kwargs = mock_clone_remote.call_args
        self.assertEqual(args[0], remote_url)
        self.assertTrue(kwargs["shallow"])

    @patch("modules.repo._clone_remote")
    def test_branch_checkout_when_provided(self, mock_clone_remote):
        """Test that the specified branch is checked out."""
        remote_url = "https://github.com/test/repo.git"
        branch = "develop"
        repo.init(origin=remote_url, branch=branch)

        mock_clone_remote.assert_called_once()
        args, kwargs = mock_clone_remote.call_args
        self.assertEqual(kwargs["branch"], branch)

    def test_runtime_registry_append_and_atomicity(self):
        """Test that the runtime registry is appended to atomically."""
        local_repo = Path(self.test_dir) / "local_repo"
        local_repo.mkdir()

        metadata1 = repo.init(origin=str(local_repo), agent_id="agent1")
        metadata2 = repo.init(origin=str(local_repo), agent_id="agent2")

        with open(self.registry_path, "r") as f:
            entries = json.load(f)
        
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["agent_id"], "agent1")
        self.assertEqual(entries[1]["agent_id"], "agent2")

    def test_uuid_generated_when_agent_id_missing(self):
        """Test that a UUID is generated when agent_id is not provided."""
        local_repo = Path(self.test_dir) / "local_repo"
        local_repo.mkdir()

        metadata = repo.init(origin=str(local_repo))
        self.assertTrue(uuid.UUID(metadata["agent_id"]))

    def test_invalid_origin_raises_useful_error(self):
        """Test that a useful error is raised for an invalid origin."""
        with self.assertRaises(FileNotFoundError):
            repo.init(origin="/non/existent/path")

        with self.assertRaises(RuntimeError):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                repo.init(origin="https://invalid/repo.git")

    def test_agent_branch_creation(self):
        """Test that a new agent-specific branch is created."""
        local_repo = Path(self.test_dir) / "local_git_repo"
        local_repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(local_repo), check=True)
        (local_repo / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=str(local_repo), check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=str(local_repo), check=True)

        task_slug = "test-task-slug"
        metadata = repo.init(origin=str(local_repo), task_slug=task_slug)

        self.assertEqual(metadata["branch"], f"agent/{task_slug}")

        current_branch = subprocess.run(
            ["git", "-C", metadata["temp_dir"], "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        self.assertEqual(current_branch, f"agent/{task_slug}")

if __name__ == "__main__":
    unittest.main()
