#!/usr/bin/env bash
# Read clipboard — Windows/VirtualBox compatible, with file fallbacks.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

PASTE_FILE="$SCRIPT_DIR/paste.txt"

read_xclip() {
    local fmt text
    for fmt in "text/plain;charset=utf-8" "text/plain" "UTF8_STRING" "STRING" "TEXT"; do
        text=$(xclip -selection clipboard -t "$fmt" -o 2>/dev/null || true)
        if [[ -n "$text" ]]; then
            printf '%s' "$text"
            return 0
        fi
    done
    xclip -selection clipboard -o 2>/dev/null || true
}

read_from_file() {
    local f
    for f in \
        "$PASTE_FILE" \
        /media/sf_clipboard/paste.txt \
        /media/sf_shared/paste.txt \
        /media/sf_*/paste.txt
    do
        # shellcheck disable=SC2086
        if [[ -f $f && -s $f ]]; then
            cat "$f"
            return 0
        fi
    done
    return 1
}

TEXT=""

# 1. Try Ubuntu clipboard (works when VirtualBox sync is on)
if command -v xclip &>/dev/null; then
    TEXT=$(read_xclip)
elif command -v xsel &>/dev/null; then
    TEXT=$(xsel --clipboard --output 2>/dev/null || true)
elif command -v wl-paste &>/dev/null; then
    TEXT=$(wl-paste --no-newline 2>/dev/null || true)
fi

# Strip null bytes from Windows clipboard
TEXT="${TEXT//$'\0'/}"

# 2. Fallback: paste.txt (manual or Windows shared folder)
if [[ -z "$TEXT" ]]; then
    TEXT=$(read_from_file || true)
fi

printf '%s' "$TEXT"