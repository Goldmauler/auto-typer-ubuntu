#!/usr/bin/env bash
# Push Auto-Typer to GitHub. Usage: ./push-to-github.sh [repo-name]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
REPO_NAME="${1:-auto-typer-ubuntu}"

if ! gh auth status &>/dev/null; then
    echo "Log in to GitHub first:"
    echo "  gh auth login"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "Creating GitHub repo: $REPO_NAME"
gh repo create "$REPO_NAME" \
    --public \
    --source=. \
    --remote=origin \
    --description "Auto-type clipboard contents on Ubuntu with Ctrl+Shift+F12" \
    --push

echo ""
echo "✅ Pushed to: $(gh repo view --json url -q .url)"