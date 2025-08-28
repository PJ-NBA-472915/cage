# Platform Manager CLI

The Platform Manager CLI provides both an interactive and a headless interface for managing the repository lifecycle.

## Interactive Mode

To launch the interactive manager, run:

```bash
python manage.py manager
```

This will present you with a menu of options to guide you through the process of initialising and closing repositories.

## Headless Mode

The headless mode is designed for scripting and automation. It provides the same functionality as the interactive mode, but through a command-line interface.

### `repo init`

Initialise a new repository.

```bash
python manage.py repo init --origin <PATH_OR_URL> [--agent-id <ID>] [--branch <BRANCH>] [--task-slug <SLUG>] [--no-shallow]
```

### `repo close`

Finalise a clone's work, commit, and push. Optionally merge the agent's branch into a target branch.

```bash
python manage.py repo close --path <PATH> --message <MESSAGE> [--agent-id <ID>] [--task-id <ID>] [--remote <REMOTE>] [--allow-empty] [--require-changes] [--signoff] [--no-verify] [--merge] [--target-branch <BRANCH>]
```

**Examples:**

**Close without merge:**
```bash
python manage.py repo close --path /tmp/repo --message "Implemented feature" --agent-id my-agent
```

**Close with merge into main:**
```bash
python manage.py repo close --path /tmp/repo --message "Bug fix" --agent-id my-agent --merge
```

**Close with merge into specific branch:**
```bash
python manage.py repo close --path /tmp/repo --message "Refactor" --agent-id my-agent --merge --target-branch develop
```
