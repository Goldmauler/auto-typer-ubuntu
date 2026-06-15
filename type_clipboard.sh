#!/usr/bin/env bash
# Called by xbindkeys when hotkey is pressed — types clipboard contents.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/auto-typer"
LOG_FILE="$STATE_DIR/auto-typer.log"
LOCK_FILE="$STATE_DIR/typing.lock"
STOP_FILE="$STATE_DIR/stop"
SPEED="${AUTO_TYPER_SPEED:-15}"
DELAY_MS=$((1000 / SPEED))
[[ "$DELAY_MS" -lt 1 ]] && DELAY_MS=1

mkdir -p "$STATE_DIR"

log() {
    echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"
}

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send -t 2500 "Auto-Typer" "$1" 2>/dev/null || true
    fi
}

# Second press while typing → stop
if [[ -f "$LOCK_FILE" ]]; then
    touch "$STOP_FILE"
    log "Stop requested"
    notify "Stopping…"
    exit 0
fi

# Read clipboard (Windows/VirtualBox compatible + paste.txt fallback)
TEXT=$(bash "$SCRIPT_DIR/read_clipboard.sh")

if [[ -z "$TEXT" ]]; then
    notify "Clipboard empty! Copy in Windows, click Ubuntu, or use paste.txt"
    log "Clipboard empty — Windows clipboard not synced? Run fix-windows-clipboard.sh"
    exit 0
fi

if ! command -v xdotool &>/dev/null; then
    notify "Missing xdotool — run install.sh"
    log "ERROR: xdotool not found"
    exit 1
fi

CHAR_COUNT=${#TEXT}
log "Typing $CHAR_COUNT chars (DISPLAY=$DISPLAY XAUTH=$XAUTHORITY)"
notify "Typing $CHAR_COUNT characters…"

touch "$LOCK_FILE"
rm -f "$STOP_FILE"
sleep 0.4

STOPPED=0
LINE_NUM=0
while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ -f "$STOP_FILE" ]]; then
        STOPPED=1
        break
    fi

    if [[ "$LINE_NUM" -gt 0 ]]; then
        xdotool key Return 2>>"$LOG_FILE" || true
        sleep 0.05
    fi

    if [[ -n "$line" ]]; then
        if ! xdotool type --delay "$DELAY_MS" -- "$line" 2>>"$LOG_FILE"; then
            log "ERROR: xdotool failed DISPLAY=$DISPLAY"
            notify "Typing failed — see log"
            rm -f "$LOCK_FILE" "$STOP_FILE"
            exit 1
        fi
    fi
    LINE_NUM=$((LINE_NUM + 1))
done <<< "$TEXT"

rm -f "$LOCK_FILE" "$STOP_FILE"

if [[ "$STOPPED" -eq 1 ]]; then
    log "Stopped mid-type"
    notify "Stopped"
else
    log "Done — typed $CHAR_COUNT chars"
    notify "Done — typed $CHAR_COUNT chars"
fi