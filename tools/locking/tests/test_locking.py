import unittest
import subprocess
import json
import os
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Assume the project root is the current working directory for tests
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
LOCK_MANAGER_SCRIPT = PROJECT_ROOT / "tools" / "locking" / "lock_manager.py"
TEST_COORDINATION_DIR = PROJECT_ROOT / "test_coordination"

class TestLockingMechanism(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure the test coordination directory is clean before all tests
        if TEST_COORDINATION_DIR.exists():
            shutil.rmtree(TEST_COORDINATION_DIR)
        TEST_COORDINATION_DIR.mkdir()

    def setUp(self):
        # Create a fresh coordination directory for each test
        self.test_dir = TEST_COORDINATION_DIR / f"test_{self._testMethodName}"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()

        # Create necessary subdirectories
        (self.test_dir / "agent_locks").mkdir()
        (self.test_dir / "heartbeats").mkdir()
        (self.test_dir / "released_locks").mkdir()

        # Create a default config.json for the test
        default_config = {
            "lock_ttl_minutes": 1, # Short TTL for testing stale locks
            "stale_grace_minutes": 0, # No grace period for testing stale locks
            "max_paths_per_claim": 25,
            "allow_topic_claims": True,
            "advisory_only": False,
            "use_flock_when_available": True,
        }
        with open(self.test_dir / "config.json", "w") as f:
            json.dump(default_config, f, indent=2)

        # Create empty registry files
        (self.test_dir / "active_work_registry.json").write_text("{}")
        (self.test_dir / "completed_work_log.json").write_text("[]")
        (self.test_dir / "planned_work_queue.json").write_text("[]")

        self.agent_id = "test_agent_1"
        self.agent_id_2 = "test_agent_2"

    def tearDown(self):
        # Clean up the test coordination directory after each test
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _run_command(self, command_args, expect_success=True):
        cmd = ["python3", str(LOCK_MANAGER_SCRIPT), "--coordination-dir", str(self.test_dir)] + command_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if expect_success:
            self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")
        return result

    def _get_active_claims(self):
        with open(self.test_dir / "active_work_registry.json", "r") as f:
            return json.load(f)

    def _get_completed_log(self):
        with open(self.test_dir / "completed_work_log.json", "r") as f:
            return json.load(f)

    def test_claim_and_release_single_file(self):
        # Claim a file
        result = self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/test_file.py", "--intent", "Test claim"])
        self.assertIn("Claim claim_", result.stdout)
        claim_id = result.stdout.split("Claim ")[1].split(" ")[0]

        active_claims = self._get_active_claims()
        self.assertIn(claim_id, active_claims)
        self.assertEqual(active_claims[claim_id]["agent_id"], self.agent_id)
        self.assertIn("src/test_file.py", active_claims[claim_id]["paths"])

        # Release the claim
        result = self._run_command(["release", "--agent", self.agent_id, "--claim-id", claim_id])
        self.assertIn(f"Claim {claim_id} successfully released", result.stdout)

        active_claims = self._get_active_claims()
        self.assertNotIn(claim_id, active_claims)

        completed_log = self._get_completed_log()
        self.assertEqual(len(completed_log), 1)
        self.assertEqual(completed_log[0]["action"], "released")
        self.assertEqual(completed_log[0]["claim_id"], claim_id)

    def test_conflict_detection_overlap(self):
        # Agent 1 claims a directory
        self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/module", "--intent", "Claim module"])
        claim_id_1 = self._get_active_claims().keys().__iter__().__next__()

        # Agent 2 tries to claim a file inside that directory
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--paths", "src/module/file.py", "--intent", "Claim file in module"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Paths ['src/module/file.py'] overlap with existing claim", result.stderr)

        # Agent 2 tries to claim the parent directory
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--paths", "src/", "--intent", "Claim parent dir"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Paths ['src'] overlap with existing claim", result.stderr)

        # Agent 2 tries to claim an overlapping file
        self._run_command(["release", "--agent", self.agent_id, "--claim-id", claim_id_1]) # Release for next test
        self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/file_a.py", "--intent", "Claim file A"])
        claim_id_a = self._get_active_claims().keys().__iter__().__next__()
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--paths", "src/file_a.py", "--intent", "Claim file A again"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Paths ['src/file_a.py'] overlap with existing claim", result.stderr)

    def test_directory_scope_claims(self):
        # Agent 1 claims a directory
        result = self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/components/", "--intent", "Claim components dir"])
        claim_id = result.stdout.split("Claim ")[1].split(" ")[0]

        active_claims = self._get_active_claims()
        self.assertIn(claim_id, active_claims)
        self.assertIn("src/components", active_claims[claim_id]["paths"])

        # Agent 2 tries to claim a file within that directory
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--paths", "src/components/button.js", "--intent", "Claim button component"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Paths ['src/components/button.js'] overlap with existing claim", result.stderr)

        # Agent 2 tries to claim the same directory
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--paths", "src/components/", "--intent", "Claim same dir"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Paths ['src/components'] overlap with existing claim", result.stderr)

    def test_stale_reap_and_audit_trail(self):
        # Agent 1 claims a file with short TTL (1 minute from setUp)
        self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/stale_file.py", "--intent", "Stale test"])
        claim_id = self._get_active_claims().keys().__iter__().__next__()

        # Wait for TTL to expire
        time.sleep(65) # 1 minute TTL + 5 seconds buffer

        # Check status - should show as stale candidate
        status_result = self._run_command(["status"])
        self.assertIn("STALE CANDIDATE", status_result.stdout)

        # Reap stale claims
        reaper_id = "auto_reaper_test"
        reap_result = self._run_command(["reap-stale", "--reaper-id", reaper_id])
        self.assertIn("Successfully reaped 1 stale claims.", reap_result.stdout)

        active_claims = self._get_active_claims()
        self.assertNotIn(claim_id, active_claims)

        completed_log = self._get_completed_log()
        self.assertEqual(len(completed_log), 1)
        self.assertEqual(completed_log[0]["action"], "reaped")
        self.assertEqual(completed_log[0]["claim_id"], claim_id)
        self.assertEqual(completed_log[0]["reaper_id"], reaper_id)
        self.assertIn("Expired and past grace period", completed_log[0]["reason"])

    def test_concurrent_claims_no_corruption(self):
        # This test aims to check for file corruption with concurrent writes.
        # Python's os.rename is atomic on POSIX, so this primarily tests the
        # atomic_write_json helper.
        num_claims = 10
        processes = []
        for i in range(num_claims):
            agent = f"agent_conc_{i}"
            path = f"src/concurrent_file_{i}.py"
            cmd = ["python3", str(LOCK_MANAGER_SCRIPT), "--coordination-dir", str(self.test_dir),
                   "claim", "--agent", agent, "--paths", path, "--intent", f"Concurrent claim {i}"]
            # Run as separate processes to simulate concurrency
            p = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(p)

        for p in processes:
            p.wait()
            self.assertEqual(p.returncode, 0, f"Concurrent claim failed: {p.stderr.read()}")

        active_claims = self._get_active_claims()
        self.assertEqual(len(active_claims), num_claims) # All claims should be successful

        # Verify each claim file exists and is valid JSON
        for claim_id, claim_data in active_claims.items():
            claim_file = self.test_dir / "agent_locks" / f"{claim_id}.json"
            self.assertTrue(claim_file.exists())
            with open(claim_file, 'r') as f:
                data = json.load(f)
                self.assertEqual(data["claim_id"], claim_id)
                self.assertEqual(data["agent_id"], claim_data["agent_id"])

    def test_resume_after_crash(self):
        # Simulate a crash during atomic write to active_work_registry.json
        # by creating a temporary file but not renaming it.
        temp_registry_file = self.test_dir / "active_work_registry.json.tmp.12345"
        with open(temp_registry_file, "w") as f:
            f.write("{\"partial_claim\": {\"agent_id\": \"crash_agent\"}}")
        
        # Clean up any orphaned temp files before running the test
        self._run_command(["cleanup"])
        
        # The system should still be able to read the original (or empty) registry
        # and not be corrupted by the partial temp file.
        # The atomic_write_json function should clean up temp files on error.
        # Here, we're testing if a *pre-existing* temp file from a crash
        # prevents the system from starting or reading.
        
        # Try to claim a new file - this should succeed and overwrite/ignore the temp file
        result = self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/new_file.py", "--intent", "Resume after crash"])
        self.assertEqual(result.returncode, 0, f"Claim failed after simulated crash: {result.stderr}")

        active_claims = self._get_active_claims()
        self.assertEqual(len(active_claims), 1) # Only the new claim should be present
        self.assertFalse(temp_registry_file.exists()) # Temp file should have been cleaned up by atomic_write_json if it was involved in a write

        # Test if a partially written claim file in agent_locks prevents reading
        partial_claim_file = self.test_dir / "agent_locks" / "partial_claim.json.tmp.abcde"
        with open(partial_claim_file, "w") as f:
            f.write("{\"claim_id\": \"partial_claim\", \"agent_id\": \"crash_agent\"") # Incomplete JSON

        # The system should ignore this partial file and not crash when listing claims
        status_result = self._run_command(["status"])
        self.assertIn("Active Claims", status_result.stdout)
        self.assertNotIn("partial_claim", status_result.stdout) # Should not show the partial claim

        # Clean up the partial claim file manually as it's not part of the atomic write flow
        if partial_claim_file.exists():
            partial_claim_file.unlink()

    def test_git_hooks_block_unclaimed_changes(self):
        # This test simulates the logic a git pre-commit hook would use.
        # It checks if a given file is covered by an active claim.
        # We'll simulate the "check if file is claimed" part.

        # Agent claims a file
        self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/claimed_file.py", "--intent", "For hook test"])
        
        # Simulate a pre-commit hook checking a claimed file
        active_claims = self._get_active_claims()
        claimed_paths = []
        for claim_data in active_claims.values():
            claimed_paths.extend(claim_data.get("paths", []))

        modified_files = ["src/claimed_file.py"] # Simulate git diff --cached --name-only

        # Check if all modified files are in claimed_paths
        all_claimed = True
        for f in modified_files:
            if f not in claimed_paths:
                all_claimed = False
                break
        self.assertTrue(all_claimed, "Modified file should be claimed")

        # Simulate a pre-commit hook checking an UNCLAIMED file
        modified_files_unclaimed = ["src/unclaimed_file.py"]
        all_claimed_unclaimed = True
        for f in modified_files_unclaimed:
            if f not in claimed_paths:
                all_claimed_unclaimed = False
                break
        self.assertFalse(all_claimed_unclaimed, "Unclaimed file should not be claimed")

    def test_lock_validate(self):
        result = self._run_command(["validate"])
        self.assertIn("Coordination directory", result.stdout)
        self.assertIn("is writable. [OK]", result.stdout)
        self.assertIn("Atomic file operations", result.stdout)
        self.assertIn("are assumed to be available and atomic", result.stdout)
        self.assertIn("Validation complete. Basic checks passed.", result.stdout)

    def test_renew_claim(self):
        # Claim a file
        result = self._run_command(["claim", "--agent", self.agent_id, "--paths", "src/renew_file.py", "--intent", "Test renew"])
        claim_id = result.stdout.split("Claim ")[1].split(" ")[0]
        
        initial_claims = self._get_active_claims()
        initial_expires_at = initial_claims[claim_id]["expires_at"]

        # Wait a bit, but not enough for it to expire
        time.sleep(1)

        # Renew the claim
        result = self._run_command(["renew", "--agent", self.agent_id, "--claim-id", claim_id])
        self.assertIn(f"Claim {claim_id} successfully renewed", result.stdout)

        renewed_claims = self._get_active_claims()
        renewed_expires_at = renewed_claims[claim_id]["expires_at"]
        renewed_at = renewed_claims[claim_id]["renewed_at"]

        self.assertGreater(renewed_expires_at, initial_expires_at)
        self.assertIsNotNone(renewed_at)
        heartbeat_file = self.test_dir / "heartbeats" / f"{self.agent_id}.heartbeat"
        self.assertTrue(heartbeat_file.exists())

    def test_agent_id_generation(self):
        result = self._run_command(["claim", "--paths", "src/gen_id.py", "--intent", "Test ID gen"])
        self.assertIn("Claim claim_", result.stdout)
        claim_id = result.stdout.split("Claim ")[1].split(" ")[0]
        
        active_claims = self._get_active_claims()
        self.assertIn(claim_id, active_claims)
        self.assertTrue(active_claims[claim_id]["agent_id"].startswith("agent_"))
        self.assertRegex(active_claims[claim_id]["agent_id"], r"agent_\d{14}_[0-9a-f]{4}")

    def test_topic_claims(self):
        # Claim a topic
        result = self._run_command(["claim", "--agent", self.agent_id, "--topics", "authentication", "--intent", "Implement auth"])
        claim_id = result.stdout.split("Claim ")[1].split(" ")[0]

        active_claims = self._get_active_claims()
        self.assertIn(claim_id, active_claims)
        self.assertIn("authentication", active_claims[claim_id]["topics"])

        # Agent 2 tries to claim the same topic
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--topics", "authentication", "--intent", "Another auth task"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict: Topics ['authentication'] overlap with existing claim", result.stderr)

        # Agent 2 tries to claim a different topic
        result = self._run_command(["claim", "--agent", self.agent_id_2, "--topics", "payments", "--intent", "Implement payments"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Claim claim_", result.stdout)

if __name__ == "__main__":
    unittest.main()