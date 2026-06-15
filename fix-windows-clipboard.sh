#!/usr/bin/env bash
# Fix Windows → Ubuntu clipboard in VirtualBox VM.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Fix Windows → Ubuntu Clipboard ==="
echo ""

# 1. Install VirtualBox guest tools
if ! dpkg -l virtualbox-guest-utils &>/dev/null; then
    echo "Installing VirtualBox Guest Additions..."
    sudo apt-get update -qq
    sudo apt-get install -y virtualbox-guest-utils virtualbox-guest-x11
else
    echo "✅ VirtualBox Guest Additions already installed"
fi

# 2. Start clipboard sync service
if command -v VBoxClient &>/dev/null; then
    VBoxClient --clipboard 2>/dev/null || true
    echo "✅ VBoxClient clipboard started"
else
    echo "⚠  VBoxClient not found — reboot may be needed"
fi

# 3. Autostart clipboard on login
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/vbox-clipboard.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=VBox Clipboard Sync
Exec=VBoxClient --clipboard
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF
echo "✅ Clipboard autostart configured"

# 4. Create paste.txt fallback
touch "$SCRIPT_DIR/paste.txt"
echo "✅ Fallback file: $SCRIPT_DIR/paste.txt"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  IMPORTANT — Do this in VirtualBox on Windows:       ║"
echo "║                                                      ║"
echo "║  1. Shut down OR focus the Ubuntu VM window          ║"
echo "║  2. VirtualBox menu → Settings → General → Advanced  ║"
echo "║  3. Shared Clipboard → set to \"Bidirectional\"       ║"
echo "║  4. Click OK, then restart Ubuntu VM                  ║"
echo "║                                                      ║"
echo "║  After reboot:                                       ║"
echo "║  • Copy in Windows (Ctrl+C)                          ║"
echo "║  • Click Ubuntu window, wait 1 second                ║"
echo "║  • Ctrl+V should paste, or Ctrl+Shift+F12 auto-types ║"
echo "║                                                      ║"
echo "║  FALLBACK (if clipboard still fails):                ║"
echo "║  Paste text into:                                    ║"
echo "║  ~/Desktop/auto-typer/paste.txt                      ║"
echo "║  Then press Ctrl+Shift+F12                           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""