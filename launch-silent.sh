#!/usr/bin/env bash
# Silent launcher — no terminal window, runs fully in background.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Already running? Just notify and exit.
if pgrep -f "xbindkeys -f $SCRIPT_DIR/xbindkeys.conf" &>/dev/null; then
    command -v notify-send &>/dev/null && \
        notify-send -t 2000 "Auto-Typer" "Already running. Hotkey: Ctrl+Shift+F12"
    exit 0
fi

nohup "$SCRIPT_DIR/start.sh" --bg >>/dev/null 2>&1 &
disown
exit 0