# Pickup Stash Skill

This skill manages session context stashes in the `.pick-up/` directory, allowing you to save your current work state and resume it in the next session.

## Usage

**Stash current session for pickup next time:**
```
/pickup-stash save
```

**Resume from previous pickup stash:**
```
/pickup-stash resume
```

## How It Works

### Save Operation
When saving a pickup stash, the skill:

1. **Creates pickup directory** if it doesn't exist
2. **Generates session context file** with:
   - Current date and status
   - All running services and their health status
   - Test repository location and contents
   - Configuration changes made during session
   - Issues resolved and solutions applied
   - Next steps and recommendations
   - Related files and artifacts created
3. **Captures relevant artifacts**:
   - Important log files from `/tmp/` or session-specific locations
   - Test output files
   - Any generated reports or documentation
4. **Creates index file** listing all stashed content with timestamps

### Resume Operation
When resuming from a pickup stash, the skill:

1. **Reads session context** from `.pick-up/session-context.md`
2. **Displays summary** of where you left off:
   - Date and status from previous session
   - Key accomplishments
   - Outstanding tasks
   - Service configurations
3. **Restores relevant state**:
   - Lists artifacts available from previous session
   - Shows command history if available
4. **Cleans up pickup directory** after confirming context has been loaded
5. **Archives old stash** to `.pick-up/archive/` with timestamp for reference

## Directory Structure

```
.pick-up/
├── session-context.md          # Main session state (created on save)
├── artifacts/                  # Session artifacts (optional)
│   ├── test-logs.txt
│   ├── integration-output.txt
│   └── ...
├── archive/                    # Old stashes (created on resume)
│   ├── 2025-10-24-session/
│   │   ├── session-context.md
│   │   └── artifacts/
│   └── ...
└── README.md                   # Instructions for manual recovery
```

## Implementation Details

### Session Context Template

The `session-context.md` file should include:

```markdown
# Session Context: [Brief Title]

**Date**: YYYY-MM-DD
**Status**: [Brief status line]

## Current State

### Services Running (X/Y)
- List of services and their status
- Ports and access points
- Health check results

### Repository/Environment
- Location of test repositories
- Key file locations
- Permissions and ownership notes

## Configuration Changes Made

### [Category 1]
- Change 1
- Change 2

### [Category 2]
- Change 1
- Change 2

## Issues Resolved

### 1. [Issue Name]
- **Error**: [Error message]
- **Cause**: [Root cause]
- **Fix**: [Solution applied]

## [Additional Sections as Needed]

## Next Steps (In Order)

1. [Immediate next task]
2. [Follow-up task]
3. [Future consideration]

## Useful Commands

```bash
# Command 1
command --flags

# Command 2
command --flags
```

## Related Files

- Path to file 1 (description)
- Path to file 2 (description)
```

### Artifacts to Capture

When saving, consider including:
- Log files from `/tmp/*-logs.txt`
- Test output from `/tmp/*-output.txt` or `/tmp/*-test*.txt`
- Generated reports
- Configuration backups
- Command history if relevant

### Cleanup Strategy

On resume:
1. Read and parse session-context.md
2. Display summary to user
3. Ask for confirmation before cleanup
4. Move entire `.pick-up/` contents to `.pick-up/archive/YYYY-MM-DD-HHMMSS-session/`
5. Create fresh `.pick-up/README.md` with basic instructions

## Example Session Context

See `.pick-up/session-context.md` (when it exists) for a real example from the validation persistence testing session.

## Safety Features

- **Never delete stashes** - always archive them
- **Confirm before cleanup** - require user confirmation
- **Preserve artifacts** - keep all logs and outputs
- **Timestamped archives** - unique names prevent overwrites
- **Git-ignored** - `.pick-up/` is in `.gitignore` to avoid commits

## Related Files

- `.gitignore` - Contains `**/.pick-up/*` to ignore stash files
- Session-specific logs in `/tmp/` (captured as artifacts)
- Generated reports in `memory-bank/reports/` (linked in context)
