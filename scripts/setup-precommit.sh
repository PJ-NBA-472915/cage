#!/bin/bash
# Setup script for pre-commit hooks
# This script installs and configures pre-commit hooks for the Cage project

set -e

echo "🔧 Setting up pre-commit hooks for Cage project..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install development dependencies
echo "📦 Installing development dependencies..."
uv sync --extra dev

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
uv run pre-commit install

# Run pre-commit on all files to check current state
echo "🔍 Running pre-commit on all files..."
uv run pre-commit run --all-files || {
    echo "⚠️  Some pre-commit checks failed. This is normal for the first run."
    echo "   The hooks will fix many issues automatically on the next commit."
    echo "   Review the output above and fix any remaining issues manually."
}

echo "✅ Pre-commit setup complete!"
echo ""
echo "Next steps:"
echo "1. Review any failed checks above"
echo "2. Fix any remaining issues manually"
echo "3. Commit your changes - pre-commit will run automatically"
echo ""
echo "Useful commands:"
echo "  uv run pre-commit run --all-files  # Run all hooks on all files"
echo "  uv run pre-commit run             # Run hooks on staged files only"
echo "  uv run pre-commit run --files <file>  # Run hooks on specific file"
