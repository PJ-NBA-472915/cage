# CLI Reference

This document provides a comprehensive reference for all available commands and options in the `manage.py` command-line interface.

## Top-Level Commands

### `health`

Performs a simple health check of the application.

**Usage:**
```bash
python manage.py health
```

### `repo`

A group of subcommands for managing repository lifecycles.

**Usage:**
```bash
python manage.py repo [SUBCOMMAND] [OPTIONS]
```

### `manager`

Launches the interactive platform manager, which provides a guided user experience for all repository operations.

**Usage:**
```bash
python manage.py manager
```
**Note:** This command requires an interactive terminal (TTY). For non-interactive environments, use the `repo` subcommands directly.

---

## `repo` Subcommands

### `init`

Initialises a working copy of a repository from a local path or a remote Git URL. It creates a unique temporary directory and a new agent-specific branch for the work.

**Usage:**
```bash
python manage.py repo init [OPTIONS]
```

**Options:**

| Option | Required | Description |
|---|---|---|
| `--origin TEXT` | **Yes** | The local filesystem path or a remote Git URL (https, ssh, or file). |
| `--agent-id TEXT` | No | A unique identifier for the agent. If not provided, a UUID will be generated. |
| `--branch TEXT` | No | The branch to check out after cloning. Defaults to the remote's default branch. |
| `--task-slug TEXT`| No | A slug for the task, used to create a new branch named `agent/<task-slug>`. If omitted, a unique slug is generated. |
| `--no-shallow` | No | If specified, a full clone will be performed instead of a shallow (depth=1) clone. |

### `close`

Finalises the work in a cloned repository. It stages all changes, creates a standardised commit message, and pushes the agent's branch to the remote. Optionally, it can also merge the agent's branch into a target branch.

**Usage:**
```bash
python manage.py repo close [OPTIONS]
```

**Options:**

| Option | Required | Description |
|---|---|---|
| `--path TEXT` | **Yes** | The path to the cloned repository directory to be closed. |
| `--message TEXT` | **Yes** | The core commit message for the work being closed. |
| `--agent-id TEXT` | No | The agent identifier. |
| `--task-id TEXT` | No | The task identifier, often included in the commit message. |
| `--remote TEXT` | No | The remote to push to. Defaults to `origin`. |
| `--allow-empty` | No | Allow an empty commit (a commit with no file changes). |
| `--require-changes`| No | Fail with an error if there are no changes to commit. |
| `--signoff` | No | Add a `Signed-off-by` trailer to the commit message. |
| `--no-verify` | No | Bypass pre-commit and commit-msg Git hooks. |
| `--merge` | No | If set, attempts to merge the agent's branch into the target branch after closing. |
| `--target-branch TEXT` | No | The branch to merge into if `--merge` is enabled. Defaults to `main`. |

**Note:** The merge functionality is now integrated into the `close` command using the `--merge` flag. The separate `merge` command has been deprecated.

**Examples:**

**Close without merge (default behavior):**
```bash
python manage.py repo close --path /tmp/agent-repo --message "Implemented new feature" --agent-id my-agent
```

**Close with merge into main:**
```bash
python manage.py repo close --path /tmp/agent-repo --message "Bug fix for issue #123" --agent-id my-agent --merge
```

**Close with merge into a specific target branch:**
```bash
python manage.py repo close --path /tmp/agent-repo --message "Refactored module" --agent-id my-agent --merge --target-branch develop
```
