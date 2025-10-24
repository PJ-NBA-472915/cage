# Resume from Previous Pickup Stash

Load the previous session context from `.pick-up/` directory and clean up the stash after confirming context has been read.

## Instructions

1. **Check if pickup stash exists**:
   ```bash
   if [ ! -f .pick-up/session-context.md ]; then
       echo "❌ No pickup stash found in .pick-up/"
       echo "💡 Use /stash-pickup to create a stash"
       exit 1
   fi
   ```

2. **Display stash summary**:
   ```bash
   echo "📦 Pickup Stash Found"
   echo "===================="
   echo ""

   # Show first few lines (header)
   head -20 .pick-up/session-context.md

   echo ""
   echo "📁 Artifacts available:"
   ls -lh .pick-up/artifacts/ 2>/dev/null || echo "  (none)"
   ```

3. **Read the full session context file**:

   Use the Read tool to load `.pick-up/session-context.md` and display it to the user.

4. **Summarize key points** for the user:

   Extract and highlight:
   - **Status**: Current state from previous session
   - **Last completed**: What was finished
   - **Next steps**: What to do next (from the stash)
   - **Blockers**: Any issues or blockers noted
   - **Artifacts**: Files available for reference

5. **List available artifacts**:
   ```bash
   if [ -d .pick-up/artifacts ]; then
       echo ""
       echo "📎 Session Artifacts:"
       find .pick-up/artifacts -type f -exec echo "  - {}" \;
   fi
   ```

6. **Ask user to confirm before cleanup**:

   Display message:
   ```
   ✅ Session context loaded!

   🗑️  Ready to archive this stash?

   The stash will be moved to:
   .pick-up/archive/YYYY-MM-DD-HHMMSS-session/

   This keeps it available for reference but clears the pickup area
   for the next session.

   Continue with archiving? (User will confirm)
   ```

7. **Archive the stash** (after user confirmation):
   ```bash
   # Create archive directory with timestamp
   TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
   ARCHIVE_DIR=".pick-up/archive/${TIMESTAMP}-session"

   mkdir -p "$ARCHIVE_DIR"

   # Move all current stash contents to archive
   mv .pick-up/session-context.md "$ARCHIVE_DIR/" 2>/dev/null || true
   mv .pick-up/artifacts "$ARCHIVE_DIR/" 2>/dev/null || true
   mv .pick-up/README.md "$ARCHIVE_DIR/" 2>/dev/null || true
   mv .pick-up/INDEX.md "$ARCHIVE_DIR/" 2>/dev/null || true

   echo "✅ Stash archived to: $ARCHIVE_DIR"
   ```

8. **Create fresh README** for next stash:
   ```bash
   cat > .pick-up/README.md << 'EOF'
   # Pickup Stash

   No active stash. Use `/stash-pickup` to save current session.

   ## Archives

   Previous stashes are in `archive/` subdirectory.
   EOF

   echo "📝 Fresh README created for next stash"
   ```

9. **Display final summary**:
   ```bash
   echo ""
   echo "✅ Resume Complete!"
   echo "=================="
   echo ""
   echo "📖 You can continue from where you left off"
   echo "📁 Previous stash archived to: $ARCHIVE_DIR"
   echo "🗂️  Artifacts preserved in archive"
   echo ""
   echo "💡 Tip: Review the 'Next Steps' section above to continue"
   ```

10. **Clean up any old archives** (optional):
    ```bash
    # Keep only last 5 archives
    cd .pick-up/archive
    ls -t | tail -n +6 | xargs rm -rf 2>/dev/null || true
    ```

## What Gets Archived

When archiving, preserve:
- ✅ `session-context.md` - Complete session state
- ✅ `artifacts/` - All session artifacts (logs, outputs, etc.)
- ✅ `README.md` - Session-specific README
- ✅ `INDEX.md` - Artifact index if present

## Archive Directory Structure

After archiving:
```
.pick-up/
├── README.md (fresh, for next stash)
└── archive/
    ├── 2025-10-24-093045-session/
    │   ├── session-context.md
    │   ├── artifacts/
    │   │   ├── test-output.txt
    │   │   └── logs.txt
    │   └── README.md
    └── 2025-10-23-141520-session/
        └── ...
```

## Safety Features

- ✅ **Never deletes** - only moves to archive
- ✅ **Timestamped archives** - unique names prevent overwrites
- ✅ **Preserves all artifacts** - logs and outputs kept
- ✅ **User confirmation** - asks before cleanup
- ✅ **Archive limit** - optionally keeps only recent archives

## Error Handling

If no stash exists:
```
❌ No pickup stash found

Looked in: .pick-up/session-context.md

💡 To create a stash:
   /stash-pickup

This will save your current session for next time.
```

If archive fails:
```
⚠️  Warning: Could not archive stash

Error: [error message]

The stash is still available at .pick-up/
You can try archiving manually or continue working.
```

## Tips for Using Resume

1. **Read context first** - Review the entire session context before continuing
2. **Check artifacts** - Look at captured logs/outputs if needed
3. **Verify state** - Confirm services/environment match what's described
4. **Update if needed** - If state has changed, note it before proceeding
5. **Start fresh** - After archiving, you can create a new stash at any time
