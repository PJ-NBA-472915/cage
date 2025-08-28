
# Repo Module

The `repo` module provides functionality for initialising a working copy of a repository from a local path or a remote Git URL. It is designed to be used by autonomous agents that need to work with a codebase in an isolated environment.

## Usage

The primary function in this module is `repo.init()`. It can be called from Python or via the `manage.py` script.

### CLI Usage

The `manage.py` script provides a `repo init` subcommand to access the `init` function.

```bash
python manage.py repo init --origin <PATH_OR_URL> [--agent-id <ID>] [--branch <BRANCH>] [--task-slug <SLUG>] [--no-shallow]
```

#### Options

- `--origin`: (Required) The local filesystem path or a remote Git URL (https, ssh, or file).
- `--agent-id`: (Optional) A unique identifier for the agent. If not provided, a UUID will be generated.
- `--branch`: (Optional) The branch to checkout after cloning.
- `--task-slug`: (Optional) A slug for the task, used to create a new agent-specific branch in the format `agent/<task-slug>`. If not provided, a unique slug will be generated.
- `--no-shallow`: (Optional) If specified, a full clone will be performed instead of a shallow clone (depth=1).

#### Examples

**Clone a remote repository and create an agent branch:**

```bash
python manage.py repo init --origin https://github.com/some-org/some-repo.git --agent-id my-agent --task-slug my-new-feature
```

**Create a working copy from a local directory:**

```bash
python manage.py repo init --origin /path/to/local/repo
```

### Python Usage

```python
from modules import repo

metadata = repo.init(
    origin="https://github.com/some-org/some-repo.git",
    agent_id="my-agent",
    task_slug="my-new-feature"
)

print(metadata)
```

## Temporary Directories and Cleanup

The `repo.init()` function creates a unique temporary directory for each initialised repository. This ensures that multiple agents can work on the same codebase without interfering with each other.

**It is the responsibility of the caller to clean up these temporary directories.** The path to the temporary directory is included in the metadata returned by the `init` function.

## Runtime Registry

The module maintains a runtime registry at `coordination/runtime_registry.json`. This is an append-only log of all repository initialisations and their lifecycle events. Each entry in the log is a JSON object containing the metadata for a session.

This registry can be used to track the activities of different agents and to manage the lifecycle of the temporary directories. It now includes detailed status updates for repository closure, including `closed`, `merged`, `conflict`, and `blocked` states, along with merge-specific metadata when applicable.

## Error Cases

The `repo.init()` function will raise an exception if:
- The `git` command is not found.
- The remote repository does not exist or is not accessible.
- The local path does not exist.
- The `coordination/runtime_registry.json` file is corrupted and cannot be parsed.

## Portability

The module is designed to be portable across macOS and Linux. It may work on Windows with WSL, but this has not been tested.

## Multi-Agent Workflows

This module is a key component of a multi-agent workflow. By providing a mechanism for creating isolated working copies of a repository, it enables multiple agents to work in parallel on different tasks.

When integrating this module into a multi-agent system, it is recommended to:
- Use a unique `agent_id` for each agent.
- Store the metadata returned by `repo.init()` in a database or other persistent storage.
- Implement a cleanup process to remove temporary directories when they are no longer needed.
- Use the runtime registry to monitor the activities of the agents.

## Repo Close Lifecycle

The `repo close` command is used to finalise the work of an agent in a cloned repository. It stages all changes, creates a standardised commit, and pushes the current agent branch to the remote. Optionally, it can also merge the agent's branch back into a target branch (e.g., `main`).

### CLI Usage

```bash
python manage.py repo close --path <PATH> --message <MESSAGE> [--agent-id <ID>] [--task-id <ID>] [--remote <REMOTE>] [--allow-empty] [--require-changes] [--signoff] [--no-verify] [--merge] [--target-branch <BRANCH>]
```

### Options

- `--path`: (Required) The path to the cloned repository.
- `--message`: (Required) The commit message.
- `--agent-id`: (Optional) The agent identifier.
- `--task-id`: (Optional) The task identifier.
- `--remote`: (Optional) The remote to push to (default: `origin`).
- `--allow-empty`: (Optional) Allow an empty commit.
- `--require-changes`: (Optional) Fail if there are no changes to commit.
- `--signoff`: (Optional) Add a `Signed-off-by` trailer to the commit message.
- `--no-verify`: (Optional) Bypass pre-commit and commit-msg hooks.
- `--merge`: (Optional) If set, attempts to merge the agent's branch into the `--target-branch` after a successful commit and push.
- `--target-branch`: (Optional) The branch to merge into if `--merge` is enabled (default: `main`).

### Merge Workflow (`--merge` flag)

When the `--merge` flag is set, the `repo close` command extends its functionality to include merging the agent's branch into a specified target branch (defaulting to `main`).

1.  **Fetch Latest:** The command first fetches the latest changes from the remote repository.
2.  **Identify Target Branch:** The target branch is identified (default `main`, configurable via `--target-branch`).
3.  **Checkout Target Branch:** The local repository checks out the target branch.
4.  **Attempt Merge:** The agent's branch is then merged into the target branch.
    *   **Fast-forward Merge:** If possible, a fast-forward merge is performed, which simply moves the branch pointer forward. No new merge commit is created.
    *   **Merge Commit:** If a fast-forward merge is not possible (i.e., there are divergent histories), a new merge commit is created with a standardized message format:
        ```
        Merge branch '{agent-branch}' into {target-branch}

        [agent:{agent}] merged after close of task {task-id}
        ```
5.  **Push Target Branch:** The merged target branch is then pushed to the remote.

### Failure Modes and Recovery

-   **Merge Conflicts:** If conflicts occur during the merge, the merge is aborted, the target branch is not modified, and the command exits with a non-zero status. The registry will record `status=conflict` along with the paths of the conflicting files.
    *   **Recovery:** In case of conflicts, the agent's branch remains pushed, and the temporary repository is *not* deleted. Manual intervention is required to resolve the conflicts in a separate environment, or the agent can re-attempt the merge after conflicts are resolved.
-   **Protected Branch:** If the target branch is detected as protected (e.g., `main` or `master` without explicit override), the merge is aborted with an error, and the failure is recorded in the registry with `status=blocked`.
    *   **Recovery:** The agent should ensure they have the necessary permissions or configure the `--target-branch` to a non-protected branch if direct merges are not allowed.
-   **Push Failures:** If the push operation (either of the agent's branch or the merged target branch) fails, the command exits with a non-zero status, and the registry will show `failure_reason: push_failed`.
    *   **Recovery:** Check network connectivity, remote repository permissions, and ensure the local branch is up-to-date with the remote.

### Registry Updates

On successful close (with or without merge), the `coordination/runtime_registry.json` is updated atomically with the following:

-   `status`: `"closed"`
-   `closed_at`: `<timestamp>`
-   `commit_sha`: `<SHA of close commit>`

If merge succeeded:

-   `merged_into`: `<branch>`
-   `merge_commit_sha`: `<SHA>` (or `commit_sha` if fast-forward)

If merge failed:

-   `status`: `"conflict"` or `"blocked"`
-   `conflict_files`: `[list of file paths]` (if conflict)
-   `failure_reason`: `"merge_conflict"` or `"protected_branch"`

### Examples

**Close without merge (default behavior):**

```bash
python manage.py repo close --path /tmp/agent-repo-123 --message "Implemented new feature" --agent-id my-agent --task-id task-abc
```

**Close with merge into `main` (fast-forward or merge commit):**

```bash
python manage.py repo close --path /tmp/agent-repo-456 --message "Bug fix for issue #123" --agent-id my-agent --task-id task-def --merge
```

**Close with merge into a specific target branch:**

```bash
python manage.py repo close --path /tmp/agent-repo-789 --message "Refactored module" --agent-id my-agent --task-id task-ghi --merge --target-branch develop
```

### Explanation of Flow

-   **Normal close (default):**
    Commit and push agent branch → registry updated with `status=closed`.
-   **Close with merge (`--merge`):**
    Commit and push agent branch → fetch and update default branch → attempt merge → push default branch → update registry with merge results.
-   **Failure modes:**
    -   Push fails → exit non-zero, registry shows `failure_reason: push_failed`.
    -   Merge conflicts → abort merge, registry shows `status=conflict` with list of files.
    -   Protected branch → registry shows `status=blocked`.


