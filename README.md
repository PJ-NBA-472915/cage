# Repo-Local Multi-Agent Locking Mechanism

This repository implements a robust, repo-local locking mechanism designed to enable multiple autonomous agents to work concurrently on the same codebase without conflicts. It provides a serverless, file-based coordination system to manage work claims, prevent overlapping edits, and maintain an auditable state.

## Key Features:

- **Concurrent Work Claims:** Agents can claim exclusive access to specific files, directories, or conceptual topics.
- **Conflict Prevention:** Automatic detection of overlapping claims prevents conflicting modifications.
- **Auditable State:** All active claims and completed work are logged in JSON registries for transparency and debugging.
- **Crash Safety:** Atomic file operations ensure data integrity even in the event of agent crashes.
- **Stale Lock Management:** Mechanisms to detect and automatically reap stale (expired) claims.
- **CLI Utilities:** A set of easy-to-use command-line tools for claiming, releasing, renewing, and monitoring locks.
- **Agent Integration Guidelines:** Comprehensive documentation on how agents should interact with the locking system, including Git etiquette and recovery procedures.

## Directory Structure:

- `./coordination/`: Contains all coordination files, including active claims, completed work logs, individual lock files, and configuration.
- `./tools/locking/`: Houses the Python-based CLI utilities (`lock-claim`, `lock-release`, `lock-status`, etc.) that agents use to interact with the locking mechanism.
- `./docs/multi-agent-locking.md`: Detailed documentation on the locking mechanism, agent integration, Git hooks, and configuration.

## Getting Started:

1.  **Explore Documentation:** Read `./docs/multi-agent-locking.md` for a full understanding of the system.
2.  **Use CLI Tools:** Navigate to `./tools/locking/` and use the provided scripts (e.g., `./lock-claim`, `./lock-status`).
3.  **Run Tests:** Execute the acceptance tests in `./tools/locking/tests/` to verify functionality.

## Example Usage:

```bash
# Claim a file
./tools/locking/lock-claim --agent "my_agent_id" --paths "src/feature_x.py" --intent "Implement feature X"

# Check current status
./tools/locking/lock-status

# Renew a claim
./tools/locking/lock-renew --agent "my_agent_id" --claim-id "claim_abcdef123456"

# Release a claim
./tools/locking/lock-release --agent "my_agent_id" --claim-id "claim_abcdef123456"

# Reap stale locks
./tools/locking/lock-reap-stale
```
