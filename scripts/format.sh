#!/usr/bin/env bash
set -e

echo "🎨 Formatting code with Ruff..."
uv run ruff format .

echo ""
echo "🔧 Auto-fixing linting issues..."
uv run ruff check --fix .

echo ""
echo "✅ Code formatted and fixed!"
