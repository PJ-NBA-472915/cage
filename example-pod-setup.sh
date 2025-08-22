#!/usr/bin/env bash
set -euo pipefail

echo "[pod-setup] Installing repo-specific tools for agent..."

# Python development tools
pip3 install --no-cache-dir black ruff mypy pytest

# Git configuration for agent
git config --global user.name "Agent-Net Bot"
git config --global user.email "agent@agentnet.local"

# Additional system packages if needed
# sudo apt-get update && sudo apt-get install -y jq htop

echo "[pod-setup] Agent setup complete."
