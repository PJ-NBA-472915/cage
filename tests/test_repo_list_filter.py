
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import repo

class TestRepoListFilter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.test_dir) / "coordination" / "runtime_registry.json"
        self.registry_path.parent.mkdir()
        repo.REGISTRY_PATH = self.registry_path

        # Create some dummy entries for testing
        self.entries = [
            {"agent_id": "agent1", "status": "initialized", "temp_dir": "/tmp/repo1"},
            {"agent_id": "agent2", "status": "in progress", "temp_dir": "/tmp/repo2"},
            {"agent_id": "agent3", "status": "conflicted", "temp_dir": "/tmp/repo3"},
            {"agent_id": "agent4", "status": "closed", "temp_dir": "/tmp/repo4"},
            {"agent_id": "agent5", "status": "merged", "temp_dir": "/tmp/repo5"},
            {"agent_id": "agent6", "status": "in progress", "temp_dir": "/tmp/repo6"},
        ]
        with open(self.registry_path, "w") as f:
            json.dump(self.entries, f, indent=2)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_open_repositories_default_filter(self):
        """Test get_open_repositories with no status filter (default behavior)."""
        expected_statuses = ["initialized", "in progress", "conflicted"]
        filtered_repos = repo.get_open_repositories()
        
        self.assertEqual(len(filtered_repos), 4)
        for r in filtered_repos:
            self.assertIn(r["status"], expected_statuses)
        
        agent_ids = {r["agent_id"] for r in filtered_repos}
        self.assertIn("agent1", agent_ids)
        self.assertIn("agent2", agent_ids)
        self.assertIn("agent3", agent_ids)
        self.assertIn("agent6", agent_ids)
        self.assertNotIn("agent4", agent_ids)
        self.assertNotIn("agent5", agent_ids)

    def test_get_open_repositories_single_status_filter(self):
        """Test get_open_repositories with a single status filter."""
        filtered_repos = repo.get_open_repositories(status_filter=["closed"])
        
        self.assertEqual(len(filtered_repos), 1)
        self.assertEqual(filtered_repos[0]["agent_id"], "agent4")
        self.assertEqual(filtered_repos[0]["status"], "closed")

    def test_get_open_repositories_multiple_status_filters(self):
        """Test get_open_repositories with multiple status filters."""
        filtered_repos = repo.get_open_repositories(status_filter=["in progress", "merged"])
        
        self.assertEqual(len(filtered_repos), 3)
        agent_ids = {r["agent_id"] for r in filtered_repos}
        self.assertIn("agent2", agent_ids)
        self.assertIn("agent5", agent_ids)
        self.assertIn("agent6", agent_ids)
        self.assertNotIn("agent1", agent_ids)
        self.assertNotIn("agent3", agent_ids)
        self.assertNotIn("agent4", agent_ids)

    def test_get_open_repositories_no_matching_status(self):
        """Test get_open_repositories when no repositories match the filter."""
        filtered_repos = repo.get_open_repositories(status_filter=["nonexistent"])
        self.assertEqual(len(filtered_repos), 0)

    def test_get_open_repositories_empty_registry(self):
        """Test get_open_repositories with an empty registry file."""
        with open(self.registry_path, "w") as f:
            json.dump([], f)
        
        filtered_repos = repo.get_open_repositories()
        self.assertEqual(len(filtered_repos), 0)

    def test_get_open_repositories_corrupted_registry(self):
        """Test get_open_repositories with a corrupted registry file."""
        with open(self.registry_path, "w") as f:
            f.write("this is not json")
        
        filtered_repos = repo.get_open_repositories()
        self.assertEqual(len(filtered_repos), 0)

if __name__ == "__main__":
    unittest.main()
