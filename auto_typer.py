#!/usr/bin/env python3
"""
Auto-Typer for Ubuntu / Linux
=============================
Listens for a global hotkey and auto-types clipboard contents character by
character at the cursor position.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time

from pynput import keyboard


# ─── Clipboard ───────────────────────────────────────────────────────────────

def _read_clipboard_command() -> list[str] | None:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()

    if session == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        if shutil.which("wl-paste"):
            return ["wl-paste", "--no-newline"]

    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard", "-o"]

    if shutil.which("xsel"):
        return ["xsel", "--clipboard", "--output"]

    if shutil.which("wl-paste"):
        return ["wl-paste", "--no-newline"]

    return None


def get_clipboard_text() -> str:
    cmd = _read_clipboard_command()
    if cmd is None:
        print("  ⚠  No clipboard tool found. Run: sudo apt install xclip")
        return ""

    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, env=env)
        if result.returncode != 0:
            print(f"  ⚠  Clipboard read failed: {result.stderr.strip()}")
            return ""
        return result.stdout
    except Exception as exc:
        print(f"  ⚠  Could not read clipboard: {exc}")
        return ""


# ─── Typer ───────────────────────────────────────────────────────────────────

class AutoTyper:
    def __init__(self, chars_per_second: float = 15.0) -> None:
        self.chars_per_second = chars_per_second
        self._typing = False
        self._stop_requested = False
        self._use_xdotool = shutil.which("xdotool") is not None

    @property
    def delay_ms(self) -> int:
        if self.chars_per_second <= 0:
            return 20
        return max(1, int(1000 / self.chars_per_second))

    def type_clipboard(self) -> None:
        if self._typing:
            print("  ⏳ Already typing — press hotkey again to stop.")
            self._stop_requested = True
            return

        text = get_clipboard_text()
        if not text:
            print("  📋 Clipboard is empty — copy text with Ctrl+C first.")
            return

        thread = threading.Thread(target=self._type_text, args=(text,), daemon=True)
        thread.start()

    def _run_xdotool(self, *args: str) -> bool:
        env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        try:
            result = subprocess.run(
                ["xdotool", *args],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            return result.returncode == 0
        except Exception as exc:
            print(f"  ⚠  xdotool error: {exc}")
            return False

    def _type_text(self, text: str) -> None:
        self._typing = True
        self._stop_requested = False

        char_count = len(text)
        backend = "xdotool" if self._use_xdotool else "pynput"
        print(f"\n  ▶  Typing {char_count} chars at {self.chars_per_second}/sec via {backend} …")

        # Let user release the hotkey before typing starts
        time.sleep(0.4)

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        if self._use_xdotool:
            self._type_with_xdotool(text)
        else:
            self._type_with_pynput(text)

        if not self._stop_requested:
            print(f"  ✅ Done — typed {char_count} characters.")
        self._typing = False
        self._stop_requested = False

    def _type_with_xdotool(self, text: str) -> None:
        lines = text.split("\n")
        for line_idx, line in enumerate(lines):
            if self._stop_requested:
                print("\n  ⏹  Stopped mid-typing.")
                return

            if line_idx > 0:
                self._run_xdotool("key", "Return")
                time.sleep(0.05)

            if line:
                if not self._run_xdotool("type", "--delay", str(self.delay_ms), "--", line):
                    print("  ⚠  xdotool failed — is DISPLAY set? Try: export DISPLAY=:0")
                    self._stop_requested = True
                    return

            if self._stop_requested:
                return

    def _type_with_pynput(self, text: str) -> None:
        from pynput.keyboard import Controller, Key

        controller = Controller()
        lines = text.split("\n")
        delay = self.delay_ms / 1000.0

        for line_idx, line in enumerate(lines):
            if self._stop_requested:
                print("\n  ⏹  Stopped mid-typing.")
                return

            if line_idx > 0:
                controller.press(Key.enter)
                controller.release(Key.enter)
                time.sleep(0.05)

            for char in line:
                if self._stop_requested:
                    return
                if char == "\t":
                    controller.press(Key.tab)
                    controller.release(Key.tab)
                else:
                    controller.type(char)
                time.sleep(delay)


# ─── Hotkey ──────────────────────────────────────────────────────────────────

def combo_to_global_hotkey(combo: str) -> str:
    """Convert 'ctrl+alt+t' → '<ctrl>+<alt>+t' for pynput GlobalHotKeys."""
    modifier_map = {
        "ctrl": "<ctrl>",
        "control": "<ctrl>",
        "shift": "<shift>",
        "alt": "<alt>",
        "option": "<alt>",
        "super": "<cmd>",
        "cmd": "<cmd>",
        "command": "<cmd>",
        "meta": "<cmd>",
    }

    parts = []
    for part in [p.strip().lower() for p in combo.split("+")]:
        if part in modifier_map:
            parts.append(modifier_map[part])
        elif len(part) == 1:
            parts.append(part)
        else:
            parts.append(f"<{part}>")

    return "+".join(parts)


def run_self_test() -> None:
    """Quick diagnostic — checks clipboard + types a test string."""
    print("\n  🔍 Running self-test …\n")

    display = os.environ.get("DISPLAY", "")
    print(f"  DISPLAY      : {display or 'NOT SET (problem!)'}")
    print(f"  Session      : {os.environ.get('XDG_SESSION_TYPE', 'unknown')}")
    print(f"  xclip        : {'yes' if shutil.which('xclip') else 'NO'}")
    print(f"  xdotool      : {'yes' if shutil.which('xdotool') else 'NO'}")
    print(f"  wl-paste     : {'yes' if shutil.which('wl-paste') else 'no'}")

    test_text = "AutoTyper test OK!"
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}

    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"], input=test_text, text=True, env=env)
        print(f"\n  📋 Put '{test_text}' on clipboard.")

    clip = get_clipboard_text()
    print(f"  📋 Read back  : {repr(clip[:40])}")

    if clip != test_text:
        print("  ❌ Clipboard test FAILED")
        sys.exit(1)

    print("\n  ⏳ Click a text field now — typing in 3 seconds …")
    time.sleep(3)

    typer = AutoTyper(chars_per_second=20)
    typer._type_text(clip)
    print("\n  ✅ Self-test complete. If you saw text appear, everything works!")
    print("  👉 Now run: ./start.sh   and use Ctrl+Alt+T to type clipboard.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-Typer for Ubuntu")
    parser.add_argument("--speed", type=float, default=15.0, help="Chars per second (default: 15)")
    parser.add_argument(
        "--hotkey",
        type=str,
        default="ctrl+alt+t",
        help='Hotkey combo (default: "ctrl+alt+t")',
    )
    parser.add_argument("--test", action="store_true", help="Run diagnostic self-test")
    args = parser.parse_args()

    if args.test:
        run_self_test()
        return

    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"
        print("  ℹ  DISPLAY was not set — using :0")

    typer = AutoTyper(chars_per_second=args.speed)
    hotkey_str = combo_to_global_hotkey(args.hotkey)

    hotkeys = {hotkey_str: typer.type_clipboard}

    hotkey_display = args.hotkey.upper().replace("+", " + ")
    clipboard_tool = _read_clipboard_command()
    clipboard_name = clipboard_tool[0] if clipboard_tool else "not found"
    typing_backend = "xdotool" if typer._use_xdotool else "pynput"

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║          🚀  AUTO-TYPER  (Ubuntu)            ║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  Hotkey    : {hotkey_display:<33s} ║")
    print(f"  ║  Speed     : {args.speed:<33.0f} ║")
    print(f"  ║  Clipboard : {clipboard_name:<33s} ║")
    print(f"  ║  Typing    : {typing_backend:<33s} ║")
    print(f"  ║  DISPLAY   : {os.environ.get('DISPLAY', ''):<33s} ║")
    print("  ║                                              ║")
    print("  ║  1. Copy text with Ctrl+C                    ║")
    print("  ║  2. Click where you want to type             ║")
    print(f"  ║  3. Press {hotkey_display:<34s} ║")
    print("  ║  4. Press hotkey again to STOP                ║")
    print("  ║                                              ║")
    print("  ║  Ctrl+C here to quit                         ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  Listening for {hotkey_str} …")
    print()

    try:
        with keyboard.GlobalHotKeys(hotkeys) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n  👋 Auto-Typer stopped. Bye!")
        sys.exit(0)


if __name__ == "__main__":
    main()