# Auto-Typer for Ubuntu

Auto-types clipboard contents character-by-character using a global hotkey. Built for Ubuntu (X11) with VirtualBox/Windows clipboard support.

## Features

- Global hotkey: **Ctrl + Shift + F12**
- Runs silently in background (no terminal window)
- VirtualBox Windows → Ubuntu clipboard support
- `paste.txt` fallback when clipboard sync fails
- Desktop notification on start/type/complete

## Quick Start

```bash
git clone https://github.com/Goldmauler/auto-typer-ubuntu.git
cd auto-typer
chmod +x *.sh
./install.sh
./launch-silent.sh
```

Then:
1. Copy text (`Ctrl+C`)
2. Click where you want to type
3. Press **Ctrl + Shift + F12**

## Commands

| Command | Description |
|---------|-------------|
| `./install.sh` | Install dependencies and set up autostart |
| `./launch-silent.sh` | Start in background (no terminal) |
| `./start.sh --test` | Self-test — types sample text after 3s |
| `./stop.sh` | Stop Auto-Typer |
| `./fix-windows-clipboard.sh` | Fix VirtualBox clipboard sync |

## VirtualBox + Windows

1. VirtualBox → VM Settings → General → Advanced → **Shared Clipboard: Bidirectional**
2. Restart Ubuntu VM
3. Run `./fix-windows-clipboard.sh`

**Fallback:** paste code into `paste.txt`, then press **Ctrl + Shift + F12**

**Shared folder (optional):** set up `C:\clipboard` on Windows, mount as `/media/sf_clipboard/`, use `windows-save-clipboard.ps1` to auto-sync.

## Files

| File | Purpose |
|------|---------|
| `type_clipboard.sh` | Types clipboard/paste.txt contents |
| `read_clipboard.sh` | Reads clipboard (Windows-compatible formats) |
| `xbindkeys.conf` | Hotkey binding |
| `launch-silent.sh` | Silent background launcher |
| `env.sh` | DISPLAY/XAUTHORITY detection |
| `windows-save-clipboard.ps1` | Windows clipboard → shared folder sync |

## Requirements

- Ubuntu with X11
- `xclip`, `xdotool`, `xbindkeys`
- `virtualbox-guest-utils` (if running in VirtualBox)

## License

MIT