#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Auto-Typer Ubuntu Setup ==="

sudo apt-get update -qq
sudo apt-get install -y xclip xdotool xbindkeys libnotify-bin virtualbox-guest-utils virtualbox-guest-x11

chmod +x "$SCRIPT_DIR"/*.sh
bash "$SCRIPT_DIR/fix-windows-clipboard.sh"
touch "$SCRIPT_DIR/paste.txt"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

# Update xbindkeys.conf with correct path (in case folder moved)
cat > "$SCRIPT_DIR/xbindkeys.conf" << EOF
# Auto-Typer hotkey — Ctrl+Shift+F12 (rarely used)
"$SCRIPT_DIR/type_clipboard.sh"
  control+shift + F12
EOF

# Generate desktop entry with correct install path
DESKTOP_FILE="$SCRIPT_DIR/auto-typer.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Auto-Typer
Comment=Type clipboard with Ctrl+Shift+F12 (no terminal)
Exec=$SCRIPT_DIR/launch-silent.sh
Icon=accessories-character-map
Terminal=false
X-GNOME-Terminal=false
StartupNotify=false
Categories=Utility;
Keywords=autotyper;typing;clipboard;hotkey;
EOF
chmod +x "$DESKTOP_FILE"

# Autostart on login (no terminal, no click needed)
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/auto-typer.desktop"

if [[ -d "$HOME/Desktop" ]]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/auto-typer.desktop"
    chmod +x "$HOME/Desktop/auto-typer.desktop"
    gio set "$HOME/Desktop/auto-typer.desktop" metadata::trusted true 2>/dev/null || true
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "  Test:    $SCRIPT_DIR/start.sh --test"
echo "  Start:   $SCRIPT_DIR/start.sh --bg"
echo "  Stop:    $SCRIPT_DIR/stop.sh"
echo "  Hotkey:  Ctrl + Shift + F12"
echo ""
echo "  Starts automatically on login. No terminal needed."
echo ""