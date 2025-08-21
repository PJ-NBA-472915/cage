#!/usr/bin/env bash
set -euo pipefail

echo "[pod-setup] Installing repo-specific tools..."

# Python development tools
pip3 install --no-cache-dir black ruff mypy

# Node.js example (uncomment if needed):
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs
# npm i -g pnpm typescript

# Additional system packages if needed
# sudo apt-get update && sudo apt-get install -y jq htop

echo "[pod-setup] Done."
