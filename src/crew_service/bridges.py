"""
Internal bridges for CrewAI service.

Provides stubbed interfaces to Files, Locks, and Tests services.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FilesBridge:
    """Bridge to Files API service."""

    def __init__(self):
        self.service_url = "http://files-api:8000"
        self.policy_enforced = True

    async def read_file(self, path: str) -> Optional[str]:
        """Read file content with policy enforcement."""
        logger.info(f"Reading file: {path}")
        # Stubbed implementation
        return f"# File content for {path}\n# This is a stubbed response"

    async def write_file(self, path: str, content: str) -> bool:
        """Write file content with policy enforcement."""
        logger.info(f"Writing file: {path}")
        # Stubbed implementation - would enforce policies
        return True

    async def list_files(self, directory: str = "") -> List[str]:
        """List files in directory with policy enforcement."""
        logger.info(f"Listing files in: {directory}")
        # Stubbed implementation
        return [f"{directory}/file1.py", f"{directory}/file2.py"]


class LocksBridge:
    """Bridge to Locks API service (in-memory stub)."""

    def __init__(self):
        self._locks: Dict[str, str] = {}  # resource -> owner
        self._acquired_locks: Dict[str, str] = {}  # owner -> resource

    async def acquire_lock(self, resource: str, owner: str) -> bool:
        """Acquire a lock on a resource."""
        logger.info(f"Acquiring lock on {resource} for {owner}")

        if resource in self._locks:
            return False  # Already locked

        self._locks[resource] = owner
        self._acquired_locks[owner] = resource
        return True

    async def release_lock(self, resource: str, owner: str) -> bool:
        """Release a lock on a resource."""
        logger.info(f"Releasing lock on {resource} for {owner}")

        if self._locks.get(resource) != owner:
            return False  # Not owned by this owner

        del self._locks[resource]
        if owner in self._acquired_locks:
            del self._acquired_locks[owner]
        return True

    async def list_locks(self) -> Dict[str, str]:
        """List all active locks."""
        logger.info("Listing all locks")
        return self._locks.copy()


class TestsBridge:
    """Bridge to Tests API service (stubbed)."""

    def __init__(self):
        self.service_url = "http://tests-api:8000"
        self.stubbed = True

    async def run_tests(self, test_path: str, timeout: int = 30) -> Dict:
        """Run tests with timeout."""
        logger.info(f"Running tests: {test_path}")
        # Stubbed implementation
        return {
            "status": "passed",
            "tests_run": 5,
            "tests_passed": 5,
            "tests_failed": 0,
            "duration": 2.5,
            "output": "All tests passed successfully",
        }

    async def get_test_results(self, run_id: str) -> Dict:
        """Get test results by run ID."""
        logger.info(f"Getting test results: {run_id}")
        # Stubbed implementation
        return {
            "run_id": run_id,
            "status": "completed",
            "results": {"passed": 5, "failed": 0, "skipped": 0},
        }


# Global bridge instances
files_bridge = FilesBridge()
locks_bridge = LocksBridge()
tests_bridge = TestsBridge()
