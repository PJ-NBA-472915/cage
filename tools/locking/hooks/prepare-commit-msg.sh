#!/bin/bash

# Git prepare-commit-msg hook for multi-agent locking mechanism
# This hook injects a summary of the agent's current claims into the commit message template.

# To bypass this hook, set the environment variable LOCK_BYPASS=1
# Example: LOCK_BYPASS=1 git commit -m "Bypass lock for emergency fix"

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"
COMMIT_SHA="$3"

if [ "$LOCK_BYPASS" = "1" ]; then
  echo "Locking prepare-commit-msg hook bypassed." >&2
  exit 0
fi

# Only run for initial commit message creation, not for --amend or other sources
if [ "$COMMIT_SOURCE" = "message" ] || [ "$COMMIT_SOURCE" = "template" ] || [ -z "$COMMIT_SOURCE" ]; then

  # Define the path to the lock-manager script relative to the project root
  LOCK_MANAGER="$(dirname "$0")"/../lock_manager.py

  # Get the agent ID from an environment variable or generate one (for testing)
  AGENT_ID="${LOCK_AGENT_ID:-$(python3 -c 'import sys; sys.path.append("tools/locking"); from lock_manager import generate_agent_id; print(generate_agent_id())')}"

  if [ -z "$AGENT_ID" ]; then
    echo "Warning: AGENT_ID not set and could not be generated. Skipping claim summary injection." >&2
    exit 0
  fi

  # Get active claims for the current agent in JSON format
  AGENT_CLAIMS_JSON=$(python3 "$LOCK_MANAGER" status --agent "$AGENT_ID" --json 2>/dev/null)

  if [ $? -ne 0 ]; then
    echo "Warning: Could not retrieve lock status for agent $AGENT_ID. Skipping claim summary injection." >&2
    exit 0
  fi

  # Parse and format claim summary
  CLAIM_SUMMARY=$(echo "$AGENT_CLAIMS_JSON" | jq -r ".active_claims | to_entries[] | select(.value.agent_id == \"$AGENT_ID\") | \"Claim ID: \" + .key + \"\n  Intent: \" + .value.intent + \"\n  Paths: \" + (.value.paths | join(\", \")) + \"\n  Topics: \" + (.value.topics | join(\", \")) + \"\n\"" 2>/dev/null)

  if [ -n "$CLAIM_SUMMARY" ]; then
    echo "\n---" >> "$COMMIT_MSG_FILE"
    echo "Agent Claims (for $AGENT_ID):" >> "$COMMIT_MSG_FILE"
    echo "$CLAIM_SUMMARY" >> "$COMMIT_MSG_FILE"
    echo "---" >> "$COMMIT_MSG_FILE"
  fi
fi

exit 0
