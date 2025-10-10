# Claude Code Configuration

This directory contains configuration files for Claude Code agents working in this repository.

## Files

### `config.json`

Permissive configuration that allows Claude Code to perform most development tasks without requiring approval for each action.

**What's Allowed:**

- ✅ All Docker and Docker Compose operations
- ✅ Running tests with pytest
- ✅ Git operations (status, diff, commit, push, etc.)
- ✅ File read/write operations (except sensitive files)
- ✅ Package management with `uv`, `pip`, `npm`, etc.
- ✅ Running development servers and services
- ✅ HTTP/HTTPS network requests
- ✅ Code formatting and linting

**What's Blocked:**

- ❌ `sudo` and privilege escalation commands
- ❌ System package managers (`apt`, `yum`, etc.)
- ❌ Modifying system directories (`/etc`, `/sys`, `/proc`)
- ❌ Accessing or modifying secrets (`.env`, `*.key`, `.ssh/`, etc.)
- ❌ Destructive Docker operations without confirmation
- ❌ Force operations without confirmation (git push --force, etc.)

**Auto-Approved Operations:**

The following commands run without requiring approval:

```bash
# Docker operations
docker-compose --profile dev up -d
docker-compose --profile dev logs -f files-api
make docker-build

# Testing
uv run pytest tests/ -v
make test-smoke

# Git read operations
git status
git diff
git log

# Development commands
uv sync
uv run uvicorn src.apps.files_api.main:app --reload
python -m pytest

# Utilities
curl, jq, grep, find, ls, cat, tail, head
```

**Requires Confirmation:**

- File deletion operations
- Git commit and push operations
- Package installation (uv/pip install)
- Docker volume removal
- Destructive operations

## Usage

Claude Code will automatically use this configuration when working in this repository. The configuration is designed to enable productive autonomous work while maintaining safety guardrails.

## Customization

You can modify `config.json` to:

1. Add more auto-approved command patterns
2. Adjust file operation permissions
3. Change workflow preferences (auto-format, auto-lint, etc.)
4. Customize project-specific settings

## Safety Features

The configuration includes multiple safety layers:

1. **Command Blocking**: Prevents sudo and system-level operations
2. **Path Exclusions**: Protects secrets and system files
3. **Confirmation Requirements**: Asks before destructive operations
4. **Operation Logging**: Records all commands and file operations

## Project-Specific Settings

The configuration includes Cage-specific preferences:

- Preferred Docker Compose profile: `dev`
- Required environment variables: `POD_TOKEN`, `REPO_PATH`
- Default test command: `uv run pytest tests/ -v`
- Main branch: `main`

## Logging

Agent activity is logged to `.claude/logs/agent-activity.log` for audit and debugging purposes.

## Security Notes

**This configuration is permissive by design** to enable autonomous agent operation. It assumes:

- The agent is operating in a development environment
- The repository is cloned in a safe location
- Sensitive data is properly excluded via `.gitignore`
- The agent follows the safety guidelines in `CLAUDE.md`

For production environments or when working with sensitive codebases, consider:

- Disabling auto-approval for more operations
- Adding additional path exclusions
- Requiring confirmation for all git operations
- Enabling stricter file operation controls

## Troubleshooting

**Agent asks for permission too often:**
- Check the `auto_approve` settings in `config.json`
- Add command patterns to `bash.auto_approve.patterns`

**Agent cannot perform needed operations:**
- Verify the command is not in `blocked_commands` or `blocked_patterns`
- Check that required paths are not in `excluded_paths`

**Want to see what the agent is doing:**
- Check `.claude/logs/agent-activity.log`
- Enable verbose logging by setting `log_level` to `DEBUG`

## References

- Main documentation: `../CLAUDE.md`
- Project README: `../README.md`
- Memory bank: `../memory-bank/`
