#!/usr/bin/env bash
# Push Auto-Typer to GitHub. Usage: ./push-to-github.sh [repo-name]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
GITHUB_USER="${GITHUB_USER:-Goldmauler}"
REPO_NAME="${1:-auto-typer-ubuntu}"
REPO_FULL="$GITHUB_USER/$REPO_NAME"

if ! gh auth status &>/dev/null; then
    echo "Log in to GitHub first:"
    echo "  gh auth login"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Create repo if it doesn't exist, then push
if ! gh repo view "$REPO_FULL" &>/dev/null; then
    echo "Creating GitHub repo: $REPO_FULL"
    gh repo create "$REPO_FULL" \
        --public \
        --description "Auto-type clipboard contents on Ubuntu with Ctrl+Shift+F12"
fi

git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$REPO_FULL.git"
git push -u origin main

echo ""
echo "✅ Pushed to: https://github.com/$REPO_FULL"