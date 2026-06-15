#!/usr/bin/env bash
STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/auto-typer"
PID_FILE="$STATE_DIR/xbindkeys.pid"

pkill -f "xbindkeys -f.*auto-typer/xbindkeys.conf" 2>/dev/null && echo "Auto-Typer stopped." || echo "Auto-Typer was not running."
rm -f "$PID_FILE"