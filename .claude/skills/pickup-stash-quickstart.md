# Pickup Stash Quick Start

Quick reference for using pickup stash commands to save and resume sessions.

## Commands

### Save Current Session
```
/stash-pickup
```
Creates a stash in `.pick-up/` with:
- Session context and state
- Configuration changes
- Issues resolved
- Next steps
- Captured artifacts (logs, outputs)

### Resume Previous Session
```
/resume-pickup
```
Loads the stash, displays summary, and archives it to `.pick-up/archive/`.

## Typical Workflow

### End of Session
```bash
# When you're done working and want to save state
/stash-pickup
```

### Start of Next Session
```bash
# When you return and want to pick up where you left off
/resume-pickup
```

## What Gets Saved

- ✅ Service status (which services running, ports, health)
- ✅ Repository/environment state
- ✅ Configuration changes (docker-compose, .env, etc.)
- ✅ Problems solved (error → cause → fix)
- ✅ Work completed and in-progress
- ✅ Prioritized next steps
- ✅ Useful commands to continue
- ✅ Environment variables needed
- ✅ Related files and artifacts
- ✅ Session logs and test outputs

## Directory Structure

```
.pick-up/
├── session-context.md          # Main context file (read this!)
├── artifacts/                  # Captured files
│   ├── test-output.txt
│   ├── integration-logs.txt
│   └── INDEX.md
├── README.md                   # Quick instructions
└── archive/                    # Old stashes
    └── 2025-10-24-093045-session/
        ├── session-context.md
        └── artifacts/
```

## Example Use Case

**End of work session:**
```
You: /stash-pickup

Claude:
✅ Session stashed for next time!

📍 Location: .pick-up/
📄 Context: .pick-up/session-context.md
📦 Artifacts: .pick-up/artifacts/

Captured:
- 10 running services (all healthy)
- Test repository: /home/planet/test_repo
- 3 configuration changes
- 2 issues resolved
- Integration test results
- Next: Document findings

To resume: /resume-pickup
```

**Next session:**
```
You: /resume-pickup

Claude:
📦 Pickup Stash Found
====================

# Session Context: Validation Persistence Testing

**Date**: 2025-10-24
**Status**: Integration test PASSED - validation confirmed working

## Current State
[... full context displayed ...]

✅ Session context loaded!

📁 Previous stash archived to: .pick-up/archive/2025-10-24-093045-session/
💡 Tip: Review the 'Next Steps' section above to continue
```

## Tips

### For Better Stashes
- Include specific error messages and solutions
- Note exact commands used for key operations
- Document any workarounds or gotchas
- List all file paths that were created/modified
- Include environment variable values needed
- Reference related documentation or reports

### For Better Resumes
- Read entire session-context.md before continuing
- Verify services/environment still match described state
- Check archived artifacts if you need logs/outputs
- Update context if anything changed since last session
- Create new stash when you make significant progress

## Manual Operations

### View Stash Without Resume
```bash
cat .pick-up/session-context.md
```

### List Artifacts
```bash
ls -lh .pick-up/artifacts/
```

### Browse Archives
```bash
ls -ltr .pick-up/archive/
cat .pick-up/archive/2025-10-24-*/session-context.md
```

### Manual Cleanup
```bash
# Archive current stash manually
timestamp=$(date +%Y-%m-%d-%H%M%S)
mv .pick-up .pick-up-archive-$timestamp
mkdir .pick-up
```

## Integration with Workflow

### With Git Workflow
```bash
# Before committing
/stash-pickup         # Save current state

git add .
git commit -m "..."
git push

# Stash preserved, ready for next session
```

### With Docker Services
```bash
# Save state of running services
/stash-pickup         # Captures service status

docker compose down   # Stop services

# Later...
/resume-pickup        # See what was running
docker compose up -d  # Restart based on context
```

### With Testing
```bash
# After test run
/stash-pickup         # Captures test outputs

# Next session
/resume-pickup        # Review test results
# Continue from test findings
```

## Troubleshooting

### No Stash Found
```
❌ No pickup stash found in .pick-up/

Solution: Use /stash-pickup to create one
```

### Stash Incomplete
If session-context.md is incomplete:
1. Read what's there: `cat .pick-up/session-context.md`
2. Manually add missing information
3. Or delete and create fresh: `rm -rf .pick-up && /stash-pickup`

### Can't Archive
If /resume-pickup fails to archive:
1. Stash remains in .pick-up/ (not lost)
2. Manually move: `mv .pick-up/.pick-up-backup`
3. Create fresh: `mkdir .pick-up`

## Related

- `.gitignore` - Contains `**/.pick-up/*` (stashes won't be committed)
- `/stash-pickup` command - Full save instructions
- `/resume-pickup` command - Full resume instructions
- `pickup-stash.md` skill - Detailed documentation
