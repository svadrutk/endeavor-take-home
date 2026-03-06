#!/usr/bin/env bash
set -e

echo "🔍 Running Ruff linter..."
uv run ruff check .

echo ""
echo "🎨 Running Ruff formatter check..."
uv run ruff format --check .

echo ""
echo "🔬 Running ty type checker..."
uv run ty check app

echo ""
echo "🧪 Running tests with coverage..."
uv run pytest

echo ""
echo "✅ All checks passed!"
