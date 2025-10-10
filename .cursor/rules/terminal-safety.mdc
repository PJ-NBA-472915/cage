---
description: Always run terminal commands through a non-interactive, timed bash subshell.
alwaysApply: true
---

## Terminal Safety Envelope

When you are about to run any console/terminal command, **do not** execute it directly.

**Always** transform the command `<cmd>` into so that it exits cleanly:
script -q /dev/null zsh -lc '<cmd>'

### Do / Don't

- ✅ Do: `npm ci` → `timeout 30s bash --noprofile --norc -lc 'npm ci' </dev/null`
- ✅ Do: `composer install --no-interaction` → `timeout 30s bash --noprofile --norc -lc 'composer install --no-interaction' </dev/null`
- ✅ Do: run all python commands using the virtual environment .venv/bin/python3
- ❌ Don't run bare commands or interactive shells (e.g., `zsh`, `bash` without this wrapper).
- ❌ Don't run devbox shell. Use "devbox run -- <cmd>" instead when executing commands in the devbox environment.

If a command is expected to stream (e.g., `tail -f`), propose a non-streaming alternative or increase the timeout only after explicit confirmation.
