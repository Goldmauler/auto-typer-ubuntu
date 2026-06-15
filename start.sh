#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/auto-typer"
PID_FILE="$STATE_DIR/xbindkeys.pid"
LOG_FILE="$STATE_DIR/auto-typer.log"
MODE="${1:-}"

mkdir -p "$STATE_DIR"

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send -t 3000 "Auto-Typer" "$1" 2>/dev/null || true
    fi
}

start_daemon() {
    # Stop old instance
    pkill -f "xbindkeys -f $SCRIPT_DIR/xbindkeys.conf" 2>/dev/null || true
    sleep 0.3

    xbindkeys -f "$SCRIPT_DIR/xbindkeys.conf" >>"$LOG_FILE" 2>&1 || true
    sleep 1

    local xb_pid
    xb_pid=$(pgrep -f "xbindkeys -f $SCRIPT_DIR/xbindkeys.conf" | head -1 || true)
    if [[ -z "$xb_pid" ]]; then
        return 1
    fi
    echo "$xb_pid" >"$PID_FILE"
    return 0
}

# ── --test ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "--test" ]]; then
    echo ""
    echo "  🔍 Auto-Typer Self-Test"
    echo "  DISPLAY=$DISPLAY"
    echo "  XAUTHORITY=$XAUTHORITY"
    echo ""
    command -v xclip    &>/dev/null && echo "  ✅ xclip"    || echo "  ❌ xclip missing"
    command -v xdotool  &>/dev/null && echo "  ✅ xdotool"  || echo "  ❌ xdotool missing"
    command -v xbindkeys &>/dev/null && echo "  ✅ xbindkeys" || echo "  ❌ xbindkeys missing"
    echo ""
    echo "test-$(date +%s)" | xclip -selection clipboard 2>/dev/null
    echo "  📋 Copied test text to clipboard."
    echo "  ⏳ Click a text field NOW — typing in 3 seconds…"
    sleep 3
    bash "$SCRIPT_DIR/type_clipboard.sh"
    echo ""
    echo "  ✅ If text appeared, Auto-Typer works!"
    echo "  👉 Start it: $SCRIPT_DIR/start.sh --bg"
    echo ""
    exit 0
fi

# ── --speed N ─────────────────────────────────────────────────────────────────
if [[ "$MODE" == "--speed" && -n "${2:-}" ]]; then
    export AUTO_TYPER_SPEED="$2"
    shift 2
    MODE="${1:-}"
fi

# ── Start daemon ──────────────────────────────────────────────────────────────
if ! start_daemon; then
    echo "  ❌ Failed to start. Log:"
    tail -8 "$LOG_FILE" 2>/dev/null
    notify "Failed to start — run install.sh"
    exit 1
fi

# ── --bg / --daemon (no terminal needed) ──────────────────────────────────────
if [[ "$MODE" == "--bg" || "$MODE" == "--daemon" ]]; then
    notify "Running! Hotkey: Ctrl+Shift+F12"
    echo "Auto-Typer running in background (PID $(cat "$PID_FILE"))."
    echo "Hotkey: Ctrl+Shift+F12  |  Stop: $SCRIPT_DIR/stop.sh"
    exit 0
fi

# ── Foreground mode (keep terminal open) ──────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║          🚀  AUTO-TYPER  (Ubuntu)            ║"
echo "  ╠══════════════════════════════════════════════╣"
echo "  ║  Status  : RUNNING                           ║"
echo "  ║  Hotkey  : Ctrl + Shift + F12                ║"
echo "  ║  Speed   : ${AUTO_TYPER_SPEED:-15} chars/sec              ║"
echo "  ║  DISPLAY : $DISPLAY"
echo "  ║                                              ║"
echo "  ║  1. Copy text  →  Ctrl+C                     ║"
echo "  ║  2. Click where you want to type             ║"
echo "  ║  3. Press      →  Ctrl + Shift + F12         ║"
echo "  ║  4. Press again to STOP mid-typing           ║"
echo "  ║                                              ║"
echo "  ║  Log: $LOG_FILE"
echo "  ║  Ctrl+C here to stop                         ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

cleanup() {
    pkill -f "xbindkeys -f $SCRIPT_DIR/xbindkeys.conf" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo ""
    echo "  👋 Auto-Typer stopped."
    exit 0
}
trap cleanup INT TERM

while pgrep -f "xbindkeys -f $SCRIPT_DIR/xbindkeys.conf" &>/dev/null; do
    sleep 2
done

echo "  ⚠  xbindkeys exited. Check: $LOG_FILE"
exit 1