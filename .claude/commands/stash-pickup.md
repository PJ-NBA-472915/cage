# Save Current Session for Pickup

Create a comprehensive stash of the current session state in `.pick-up/` directory for resuming work in the next session.

## Instructions

1. **Create pickup directory structure**:
   ```bash
   mkdir -p .pick-up/artifacts
   ```

2. **Generate session context file** (`.pick-up/session-context.md`):

   Include the following sections based on current session:

   - **Header**: Date, status, brief summary
   - **Current State**:
     - Services running (with health status)
     - Repository/environment details
     - Key file locations
   - **Configuration Changes**: Any docker-compose.yml, .env, or config updates
   - **Issues Resolved**: Problems fixed during session with error/cause/fix
   - **Work Completed**: Major accomplishments
   - **Next Steps**: Prioritized list of what to do next
   - **Useful Commands**: Key commands for continuing work
   - **Related Files**: Paths to important files created/modified
   - **Environment Variables**: Required env vars and their values

3. **Capture session artifacts**:

   Copy relevant files to `.pick-up/artifacts/`:
   ```bash
   # Example artifacts to capture:
   cp /tmp/*-test*.txt .pick-up/artifacts/ 2>/dev/null || true
   cp /tmp/*-logs.txt .pick-up/artifacts/ 2>/dev/null || true
   cp /tmp/*-output.txt .pick-up/artifacts/ 2>/dev/null || true
   ```

4. **Create artifact index** (`.pick-up/artifacts/INDEX.md`):
   ```markdown
   # Session Artifacts

   **Captured**: YYYY-MM-DD HH:MM:SS

   ## Files
   - `file1.txt` - Description
   - `file2.log` - Description

   ## Usage
   Files from previous session available for reference or continuation of work.
   ```

5. **Create README** (`.pick-up/README.md`):
   ```markdown
   # Pickup Stash

   This directory contains saved session state for resuming work.

   ## Main File
   - `session-context.md` - Complete session state and next steps

   ## To Resume
   Read `session-context.md` to understand where you left off.

   ## To Stash Again
   Use `/stash-pickup` command to save current session.

   ## To Clean Up After Resume
   Use `/resume-pickup` command which will archive this stash.
   ```

6. **Verify stash was created**:
   ```bash
   ls -la .pick-up/
   echo "✅ Session stashed successfully in .pick-up/"
   echo "📁 Contents:"
   tree .pick-up/ -L 2 || find .pick-up/ -type f
   ```

7. **Display confirmation** to user:
   ```
   ✅ Session stashed for next time!

   📍 Location: .pick-up/
   📄 Context: .pick-up/session-context.md
   📦 Artifacts: .pick-up/artifacts/

   To resume: /resume-pickup
   ```

## Example Session Context Template

Use this template and fill in with current session details:

```markdown
# Session Context: [Brief Title]

**Date**: YYYY-MM-DD
**Status**: [One-line status]

## Current State

### Services Running (X/Y)
List all services with status and ports.

### Repository/Environment
- **Location**: /path/to/repo
- **Branch**: branch-name
- **Key files**: List important files

## Configuration Changes Made

### docker-compose.yml
- Change 1
- Change 2

### Other Config
- Change 1
- Change 2

## Issues Resolved

### 1. Issue Name
- **Error**: Error message
- **Cause**: Root cause
- **Fix**: Solution applied

## Work Completed

- [ ] Task 1
- [x] Task 2 (completed)
- [ ] Task 3

## Next Steps (In Order)

1. Immediate next action
2. Follow-up task
3. Future consideration

## Useful Commands

```bash
# Command to continue work
command --here

# Command to check status
another-command
```

## Environment Variables

```bash
export VAR1="value"
export VAR2="value"
```

## Related Files

- `.pick-up/artifacts/test-output.txt` - Test execution results
- `memory-bank/reports/YYYY-MM-DD-report.md` - Detailed report
- `path/to/file.ext` - Description

## Notes

Any additional context or gotchas to remember.
```

## Tips

- Be comprehensive - include everything needed to pick up exactly where you left off
- Include both successes AND blockers/issues
- List all environment setup (env vars, service configs, etc.)
- Reference all created/modified files
- Provide clear next steps prioritized by importance
- Include relevant command examples for quick reference
