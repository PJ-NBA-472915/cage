
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
- `--task-slug`: (Optional) A slug for the task, used to create a new agent-specific branch in the format `agent/<task-slug>`.
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

The module maintains a runtime registry at `coordination/runtime_registry.json`. This is an append-only log of all repository initialisations. Each entry in the log is a JSON object containing the metadata for a session.

This registry can be used to track the activities of different agents and to manage the lifecycle of the temporary directories.

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
