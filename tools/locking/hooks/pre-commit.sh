#!/bin/bash

# Git pre-commit hook for multi-agent locking mechanism
# This hook prevents committing changes to files that are not covered by an active claim
# held by the current agent.

# To bypass this hook, set the environment variable LOCK_BYPASS=1
# Example: LOCK_BYPASS=1 git commit -m "Bypass lock for emergency fix"

if [ "$LOCK_BYPASS" = "1" ]; then
  echo "Locking pre-commit hook bypassed." >&2
  exit 0
fi

# Define the path to the lock-manager script relative to the project root
LOCK_MANAGER="$(dirname "$0")"/../lock_manager.py

# Get the agent ID from an environment variable or generate one (for testing)
# In a real agent setup, AGENT_ID would be consistently set for the agent process.
AGENT_ID="${LOCK_AGENT_ID:-$(python3 -c 'import sys; sys.path.append("tools/locking"); from lock_manager import generate_agent_id; print(generate_agent_id())')}"

if [ -z "$AGENT_ID" ]; then
  echo "Error: AGENT_ID not set and could not be generated. Cannot run lock pre-commit check." >&2
  exit 1
fi

# Get staged files that are being modified
MODIFIED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$MODIFIED_FILES" ]; then
  echo "No modified files to check." >&2
  exit 0
fi

# Get active claims for the current agent in JSON format
AGENT_CLAIMS_JSON=$(python3 "$LOCK_MANAGER" status --agent "$AGENT_ID" --json 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "Error: Could not retrieve lock status. Aborting commit." >&2
  exit 1
fi

# Parse claimed paths from the JSON output
CLAIMED_PATHS=$(echo "$AGENT_CLAIMS_JSON" | jq -r ".active_claims | to_entries[] | select(.value.agent_id == \"$AGENT_ID\") | .value.paths[]" 2>/dev/null)

UNCLAIMED_MODIFICATIONS=()

for FILE in $MODIFIED_FILES; do
  IS_CLAIMED=false
  for CLAIMED_PATH in $CLAIMED_PATHS; do
    # Check for exact file match or if file is within a claimed directory
    if [[ "$FILE" == "$CLAIMED_PATH" ]] || [[ "$FILE" == "$CLAIMED_PATH"/* ]]; then
      IS_CLAIMED=true
      break
    fi
  done
  if ! $IS_CLAIMED; then
    UNCLAIMED_MODIFICATIONS+=("$FILE")
  fi
done

if [ ${#UNCLAIMED_MODIFICATIONS[@]} -gt 0 ]; then
  echo "" >&2
  echo "ERROR: Cannot commit. The following modified files are not covered by your active claims:" >&2
  for FILE in "${UNCLAIMED_MODIFICATIONS[@]}"; do
    echo "  - $FILE" >&2
  done
  echo "" >&2
  echo "Please claim these files using './tools/locking/lock-claim' or bypass with LOCK_BYPASS=1." >&2
  exit 1
fi

echo "All modified files are covered by active claims. Proceeding with commit." >&2
exit 0
