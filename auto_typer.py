#!/usr/bin/env python3
"""
Auto-Typer — cross-platform (Windows + Ubuntu/Linux)
Listens for a global hotkey and auto-types clipboard contents character by
character at the cursor position. Press the hotkey again to interrupt/stop.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from pynput import keyboard

SCRIPT_DIR = Path(__file__).resolve().parent
PASTE_FILE = SCRIPT_DIR / "paste.txt"
CONFIG_FILE = SCRIPT_DIR / "config.txt"
CHECKPOINT_FILE = SCRIPT_DIR / "checkpoint.json"
IS_WINDOWS = sys.platform == "win32"


# ─── Clipboard ───────────────────────────────────────────────────────────────

def _init_windows_clipboard_api() -> tuple[ctypes.WinDLL, ctypes.WinDLL]:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HGLOBAL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HGLOBAL]
    user32.SetClipboardData.restype = wintypes.HANDLE

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    return user32, kernel32


def _get_clipboard_windows() -> str:
    CF_UNICODETEXT = 13
    user32, kernel32 = _init_windows_clipboard_api()

    for _ in range(5):
        if not user32.OpenClipboard(None):
            time.sleep(0.02)
            continue
        try:
            if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return ""
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.c_wchar_p(pointer).value or ""
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    return ""


def _set_clipboard_windows(text: str) -> bool:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    user32, kernel32 = _init_windows_clipboard_api()

    for _ in range(5):
        if not user32.OpenClipboard(None):
            time.sleep(0.02)
            continue
        try:
            user32.EmptyClipboard()
            data = text.encode("utf-16-le") + b"\x00\x00"
            handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not handle:
                return False
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return False
            ctypes.memmove(pointer, data, len(data))
            kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                return False
            return True
        finally:
            user32.CloseClipboard()
    return False


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


def _read_paste_file() -> str:
    if PASTE_FILE.is_file() and PASTE_FILE.stat().st_size > 0:
        return PASTE_FILE.read_text(encoding="utf-8", errors="replace")
    return ""


def get_clipboard_text() -> str:
    text = ""

    if IS_WINDOWS:
        try:
            text = _get_clipboard_windows()
        except Exception as exc:
            print(f"  ⚠  Could not read clipboard: {exc}")
    else:
        cmd = _read_clipboard_command()
        if cmd is None:
            print("  ⚠  No clipboard tool found. Run: sudo apt install xclip")
        else:
            env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, env=env)
                if result.returncode == 0:
                    text = result.stdout
                else:
                    print(f"  ⚠  Clipboard read failed: {result.stderr.strip()}")
            except Exception as exc:
                print(f"  ⚠  Could not read clipboard: {exc}")

    text = text.replace("\x00", "")

    if not text.strip():
        text = _read_paste_file()

    return text


# ─── Config ──────────────────────────────────────────────────────────────────

def parse_bool_config(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict[str, str]:
    defaults = {
        "hotkey": "ctrl+shift+f12" if IS_WINDOWS else "ctrl+alt+t",
        "reset_hotkey": "ctrl+shift+f11" if IS_WINDOWS else "ctrl+shift+f11",
        "speed": "40",
        "human_delay": "false",
        "indent_mode": "editor" if IS_WINDOWS else "literal",
    }
    if not CONFIG_FILE.is_file():
        return defaults

    config = dict(defaults)
    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            config[key.strip().lower()] = value.strip()
    return config


def save_config(
    hotkey: str,
    speed: float,
    human_delay: bool = True,
    indent_mode: str = "editor",
) -> None:
    CONFIG_FILE.write_text(
        f"# Auto-Typer config — edit hotkey and speed here\n"
        f"hotkey={hotkey}\n"
        f"speed={speed}\n"
        f"human_delay={str(human_delay).lower()}\n"
        f"indent_mode={indent_mode}\n",
        encoding="utf-8",
    )


# ─── Indentation (line-based, exact) ─────────────────────────────────────────

TAB_WIDTH = 4


def measure_indent(line: str, tab_width: int = TAB_WIDTH) -> int:
    width = 0
    for char in line:
        if char == " ":
            width += 1
        elif char == "\t":
            width += tab_width
        else:
            break
    return width


def expected_editor_indent(prev_line: str, prev_indent: int, tab_width: int = TAB_WIDTH) -> int:
    stripped = prev_line.rstrip()
    if not stripped:
        return prev_indent
    if stripped.endswith((":", "{", "[", "(", "\\")):
        return prev_indent + tab_width
    return prev_indent


def build_line_offsets(text: str) -> list[tuple[str, int, int]]:
    """Return (line_text, start_pos, end_pos) where end_pos is after the newline."""
    lines = text.split("\n")
    offsets: list[tuple[str, int, int]] = []
    pos = 0
    for index, line in enumerate(lines):
        start = pos
        pos += len(line)
        if index < len(lines) - 1:
            pos += 1
        offsets.append((line, start, pos))
    return offsets


def find_line_index(offsets: list[tuple[str, int, int]], position: int) -> int:
    for index, (_, start, end) in enumerate(offsets):
        if start <= position < end:
            return index
    return max(0, len(offsets) - 1)


# ─── Checkpoint ──────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:16]


def format_checkpoint_context(text: str, position: int) -> dict[str, str | int]:
    typed = text[:position]
    line = typed.count("\n") + 1
    line_start = typed.rfind("\n") + 1
    column = position - line_start + 1
    next_chars = text[position : position + 40].replace("\n", "\\n")
    last_typed = typed[max(0, len(typed) - 50) :].replace("\n", "\\n")
    return {
        "line": line,
        "column": column,
        "last_typed": last_typed,
        "next_chars": next_chars,
    }


def save_checkpoint(text: str, position: int, indent_mode: str = "editor") -> None:
    normalized = normalize_text(text)
    position = max(0, min(position, len(normalized)))
    context = format_checkpoint_context(normalized, position)
    CHECKPOINT_FILE.write_text(
        json.dumps(
            {
                "text": normalized,
                "position": position,
                "total": len(normalized),
                "fingerprint": text_fingerprint(normalized),
                "line": context["line"],
                "column": context["column"],
                "last_typed": context["last_typed"],
                "next_chars": context["next_chars"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_checkpoint() -> dict | None:
    if not CHECKPOINT_FILE.is_file():
        return None
    try:
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        position = int(data.get("position", 0))
        total = int(data.get("total", 0))
        if 0 <= position < total and data.get("text"):
            return data
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def clear_checkpoint() -> None:
    CHECKPOINT_FILE.unlink(missing_ok=True)


def resolve_typing_job(
    clipboard_text: str,
    indent_mode: str = "editor",
) -> tuple[str, int, bool, dict | None]:
    """Return (text, start_position, is_resume, checkpoint_meta)."""
    checkpoint = load_checkpoint()
    clipboard_text = normalize_text(clipboard_text)

    if checkpoint:
        saved_text = checkpoint["text"]
        saved_pos = int(checkpoint["position"])
        same_text = (
            clipboard_text
            and text_fingerprint(clipboard_text) == checkpoint.get("fingerprint")
        )

        if same_text or (not clipboard_text and saved_pos < len(saved_text)):
            return saved_text, saved_pos, True, checkpoint

        if clipboard_text and not same_text:
            clear_checkpoint()
            return clipboard_text, 0, False, None

        if saved_pos < len(saved_text):
            return saved_text, saved_pos, True, checkpoint

    if not clipboard_text:
        return "", 0, False, None

    clear_checkpoint()
    return clipboard_text, 0, False, None


# ─── Typer ───────────────────────────────────────────────────────────────────

class AutoTyper:
    def __init__(
        self,
        chars_per_second: float = 40.0,
        human_delay: bool = True,
        indent_mode: str = "editor",
    ) -> None:
        self.chars_per_second = chars_per_second
        self.human_delay = human_delay
        self.indent_mode = indent_mode if indent_mode in {"editor", "literal"} else "editor"
        self._typing = False
        self._stop_after_line = False
        self._reset_requested = False
        self._use_xdotool = (not IS_WINDOWS) and shutil.which("xdotool") is not None

    @property
    def delay_ms(self) -> int:
        if self.chars_per_second <= 0:
            return 120
        return max(1, int(1000 / self.chars_per_second))

    def _delay_after_char(self, char: str, next_char: str | None = None) -> float:
        """Return seconds to wait after typing a character (human-like rhythm)."""
        base = 1.0 / max(self.chars_per_second, 1.0)

        if not self.human_delay:
            return base

        delay = base * random.uniform(0.9, 1.15)

        if char in ".!?":
            delay += random.uniform(0.08, 0.18)
        elif char in ",;:":
            delay += random.uniform(0.04, 0.10)
        elif char == "\n":
            delay += random.uniform(0.12, 0.22)
        elif char in "({[":
            delay += random.uniform(0.03, 0.08)
        elif char in ")}]":
            delay += random.uniform(0.03, 0.09)
        elif char == " " and next_char and next_char in "({[":
            delay += random.uniform(0.02, 0.06)

        if random.random() < 0.02:
            delay += random.uniform(0.06, 0.14)

        return max(0.03, delay)

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep in small slices; return True only if reset was requested."""
        if seconds <= 0:
            return self._reset_requested
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._reset_requested:
                return True
            time.sleep(min(0.015, end - time.monotonic()))
        return self._reset_requested

    def _speed_label(self) -> str:
        if self.human_delay:
            return f"~{self.chars_per_second:.0f} cps (normal)"
        return f"{self.chars_per_second:.0f} cps (steady)"

    def request_stop_after_line(self) -> None:
        if self._typing:
            print("  ⏳ Finishing current line, then stopping …")
            self._stop_after_line = True
            return

        self.type_clipboard()

    def reset_typing(self) -> None:
        clear_checkpoint()
        self._stop_after_line = False
        if self._typing:
            print("  🔄 Reset — stopping now. Next F12 starts from the beginning.")
            self._reset_requested = True
        else:
            print("  🔄 Reset — checkpoint cleared. F12 starts from the beginning.")

    def type_clipboard(self) -> None:
        clipboard_text = get_clipboard_text()
        text, start_pos, is_resume, checkpoint_meta = resolve_typing_job(
            clipboard_text,
            self.indent_mode,
        )

        if not text:
            print("  📋 Clipboard is empty — copy text with Ctrl+C first (or use paste.txt).")
            return

        if is_resume:
            ctx = format_checkpoint_context(text, start_pos)
            print(
                f"  ▶  Resuming at line {ctx['line']} col {ctx['column']} "
                f"({len(text) - start_pos} chars left)"
            )
            print(f"  👉 Cursor at start of line {ctx['line']}. Next: {ctx['next_chars']!r}")
            if checkpoint_meta and checkpoint_meta.get("last_typed"):
                print(f"  ↩  Previous line ended: ...{checkpoint_meta['last_typed']!r}")
        else:
            clear_checkpoint()
            print(f"  ▶  Starting from beginning ({len(text)} chars) …")

        thread = threading.Thread(
            target=self._type_text,
            args=(text, start_pos),
            daemon=True,
        )
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

    def _type_text(self, text: str, start_pos: int = 0) -> None:
        self._typing = True
        self._stop_after_line = False
        self._reset_requested = False

        text = normalize_text(text)
        total = len(text)
        remaining = total - start_pos
        backend = "xdotool" if self._use_xdotool else "pynput"

        speed_label = self._speed_label()
        if start_pos == 0:
            print(f"\n  ▶  Typing {total} chars at {speed_label} via {backend} …")
        else:
            print(f"\n  ▶  Continuing {remaining} chars at {speed_label} via {backend} …")

        if start_pos > 0:
            ctx = format_checkpoint_context(text, start_pos)
            print(
                f"  ⏳ Resuming in 0.5s at line {ctx['line']} — "
                f"leave cursor at end of last typed line …"
            )
            if self._interruptible_sleep(0.5):
                self._typing = False
                self._reset_requested = False
                return
        else:
            if self._interruptible_sleep(0.4):
                self._typing = False
                self._reset_requested = False
                return

        if self._use_xdotool:
            end_pos, stopped = self._type_with_xdotool(text, start_pos)
        else:
            end_pos, stopped = self._type_with_pynput(text, start_pos)

        if self._reset_requested:
            clear_checkpoint()
            print("\n  🔄 Typing aborted. Press F12 to start from the beginning.")
        elif stopped:
            stop_pos = end_pos
            save_checkpoint(text, stop_pos, self.indent_mode)
            ctx = format_checkpoint_context(text, stop_pos)
            print(
                f"\n  ⏹  Stopped at line {ctx['line']} col {ctx['column']} "
                f"({stop_pos}/{total})"
            )
            print(f"  💾 Checkpoint saved. Next line: {ctx['next_chars']!r}")
            print("  👉 Cursor on the next empty line. Press F12 to resume.")
        else:
            clear_checkpoint()
            print(f"  ✅ Done — typed {total} characters.")

        self._typing = False
        self._stop_after_line = False
        self._reset_requested = False

    def _type_string_xdotool(self, content: str, start_index: int, full_text: str) -> tuple[int, bool]:
        index = start_index
        for offset, char in enumerate(content):
            if self._reset_requested:
                return index, False

            next_char = content[offset + 1] if offset + 1 < len(content) else None
            if char == "\t":
                if not self._run_xdotool("key", "Tab"):
                    return index, True
            else:
                if not self._run_xdotool("type", "--delay", "0", "--", char):
                    return index, True

            index += 1
            if self._interruptible_sleep(self._delay_after_char(char, next_char)):
                return index, False

        return index, False

    def _prepare_new_line_xdotool(self, prev_line: str) -> bool:
        if not self._run_xdotool("key", "Return"):
            return False
        if self._interruptible_sleep(0.12):
            return False
        if self.indent_mode == "editor":
            prev_indent = measure_indent(prev_line)
            editor_indent = expected_editor_indent(prev_line, prev_indent)
            for _ in range(editor_indent):
                if self._reset_requested:
                    return False
                if not self._run_xdotool("key", "BackSpace"):
                    return False
            if self._interruptible_sleep(0.03):
                return False
        return True

    def _type_with_xdotool(self, text: str, start_pos: int = 0) -> tuple[int, bool]:
        offsets = build_line_offsets(text)
        if not offsets:
            return 0, False

        line_index = find_line_index(offsets, start_pos)
        col_offset = start_pos - offsets[line_index][1]

        for index in range(line_index, len(offsets)):
            line, line_start, line_end = offsets[index]

            if self._reset_requested:
                return line_start if col_offset == 0 else start_pos, False

            if index == line_index and col_offset > 0:
                typed_end, failed = self._type_string_xdotool(
                    line[col_offset:], line_start + col_offset, text
                )
                if failed or self._reset_requested:
                    return typed_end, False
                if self._stop_after_line:
                    return line_end, True
                col_offset = 0
                continue

            if index > line_index:
                if not self._prepare_new_line_xdotool(offsets[index - 1][0]):
                    return line_start, True
                if self._reset_requested:
                    return line_start, False
                if self._stop_after_line:
                    return line_start, True

            typed_end, failed = self._type_string_xdotool(line, line_start, text)
            if failed or self._reset_requested:
                return typed_end, False
            if self._stop_after_line:
                if index < len(offsets) - 1:
                    if not self._prepare_new_line_xdotool(line):
                        return line_end, True
                    return offsets[index + 1][1], True
                return line_end, False

        return len(text), False

    def _type_string_pynput(self, controller, content: str, start_index: int) -> tuple[int, bool]:
        from pynput.keyboard import Key

        index = start_index
        for offset, char in enumerate(content):
            if self._reset_requested:
                return index, False

            next_char = content[offset + 1] if offset + 1 < len(content) else None
            if char == "\t":
                controller.press(Key.tab)
                controller.release(Key.tab)
            elif char == " ":
                controller.press(Key.space)
                controller.release(Key.space)
            else:
                controller.type(char)

            index += 1
            if self._interruptible_sleep(self._delay_after_char(char, next_char)):
                return index, False

        return index, False

    def _prepare_new_line_pynput(self, controller, prev_line: str) -> bool:
        from pynput.keyboard import Key

        controller.press(Key.enter)
        controller.release(Key.enter)
        if self._interruptible_sleep(0.12):
            return False
        if self.indent_mode == "editor":
            prev_indent = measure_indent(prev_line)
            editor_indent = expected_editor_indent(prev_line, prev_indent)
            for _ in range(editor_indent):
                if self._reset_requested:
                    return False
                controller.press(Key.backspace)
                controller.release(Key.backspace)
            if self._interruptible_sleep(0.03):
                return False
        return True

    def _type_with_pynput(self, text: str, start_pos: int = 0) -> tuple[int, bool]:
        from pynput.keyboard import Controller

        controller = Controller()
        offsets = build_line_offsets(text)
        if not offsets:
            return 0, False

        line_index = find_line_index(offsets, start_pos)
        col_offset = start_pos - offsets[line_index][1]

        for index in range(line_index, len(offsets)):
            line, line_start, line_end = offsets[index]

            if self._reset_requested:
                return line_start if col_offset == 0 else start_pos, False

            if index == line_index and col_offset > 0:
                typed_end, failed = self._type_string_pynput(
                    controller, line[col_offset:], line_start + col_offset
                )
                if failed or self._reset_requested:
                    return typed_end, False
                if self._stop_after_line:
                    return line_end, True
                col_offset = 0
                continue

            if index > line_index:
                if not self._prepare_new_line_pynput(controller, offsets[index - 1][0]):
                    return line_start, True
                if self._reset_requested:
                    return line_start, False
                if self._stop_after_line:
                    return line_start, True

            typed_end, failed = self._type_string_pynput(controller, line, line_start)
            if failed or self._reset_requested:
                return typed_end, False
            if self._stop_after_line:
                if index < len(offsets) - 1:
                    if not self._prepare_new_line_pynput(controller, line):
                        return line_end, True
                    return offsets[index + 1][1], True
                return line_end, False

        return len(text), False


# ─── Hotkey ──────────────────────────────────────────────────────────────────

def combo_to_global_hotkey(combo: str) -> str:
    """Convert 'ctrl+shift+f12' → '<ctrl>+<shift>+<f12>' for pynput GlobalHotKeys."""
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
        "win": "<cmd>",
        "windows": "<cmd>",
    }

    function_keys = {f"f{i}" for i in range(1, 25)}

    parts = []
    for part in [p.strip().lower() for p in combo.split("+")]:
        if part in modifier_map:
            parts.append(modifier_map[part])
        elif part in function_keys:
            parts.append(f"<{part}>")
        elif len(part) == 1:
            parts.append(part)
        else:
            parts.append(f"<{part}>")

    return "+".join(parts)


def run_self_test() -> None:
    print("\n  🔍 Running self-test …\n")

    if IS_WINDOWS:
        print(f"  Platform     : Windows")
        _set_clipboard_windows("AutoTyper test OK!")
        print("  📋 Put 'AutoTyper test OK!' on clipboard.")
    else:
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

    if "AutoTyper test OK!" not in clip:
        print("  ❌ Clipboard test FAILED")
        sys.exit(1)

    print("\n  ⏳ Click a text field now — typing in 3 seconds …")
    time.sleep(3)

    typer = AutoTyper(chars_per_second=20)
    typer._type_text(clip)
    print("\n  ✅ Self-test complete. If you saw text appear, everything works!")
    platform_hint = "start-windows.bat" if IS_WINDOWS else "./start.sh"
    print(f"  👉 Now run: {platform_hint}\n")


def main() -> None:
    config = load_config()

    parser = argparse.ArgumentParser(description="Auto-Typer (Windows + Ubuntu)")
    parser.add_argument("--speed", type=float, default=float(config.get("speed", "40")),
                        help="Average chars per second (default: 40)")
    parser.add_argument(
        "--indent-mode",
        type=str,
        choices=["editor", "literal"],
        default=config.get("indent_mode", "editor" if IS_WINDOWS else "literal"),
        help="editor=IDE auto-indent (VS Code/Cursor), literal=type all spaces (Notepad)",
    )
    parser.add_argument(
        "--human-delay",
        action=argparse.BooleanOptionalAction,
        default=parse_bool_config(config.get("human_delay", "true")),
        help="Human-like variable delays between keys (default: on)",
    )
    parser.add_argument(
        "--hotkey",
        type=str,
        default=config.get("hotkey", "ctrl+shift+f12" if IS_WINDOWS else "ctrl+alt+t"),
        help='Start / resume / stop-after-line (default: "ctrl+shift+f12")',
    )
    parser.add_argument(
        "--reset-hotkey",
        type=str,
        default=config.get("reset_hotkey", "ctrl+shift+f11"),
        help='Reset to beginning (default: "ctrl+shift+f11")',
    )
    parser.add_argument("--test", action="store_true", help="Run diagnostic self-test")
    parser.add_argument("--save-config", action="store_true",
                        help="Save --hotkey and --speed to config.txt")
    args = parser.parse_args()

    if args.save_config:
        save_config(args.hotkey, args.speed, args.human_delay, args.indent_mode)
        print(
            f"  💾 Saved config: hotkey={args.hotkey}, "
            f"speed={args.speed}, human_delay={args.human_delay}, "
            f"indent_mode={args.indent_mode}"
        )

    if args.test:
        run_self_test()
        return

    if not IS_WINDOWS and not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"
        print("  ℹ  DISPLAY was not set — using :0")

    typer = AutoTyper(
        chars_per_second=args.speed,
        human_delay=args.human_delay,
        indent_mode=args.indent_mode,
    )
    hotkey_str = combo_to_global_hotkey(args.hotkey)
    reset_hotkey_str = combo_to_global_hotkey(args.reset_hotkey)

    hotkeys = {
        hotkey_str: typer.request_stop_after_line,
        reset_hotkey_str: typer.reset_typing,
    }

    hotkey_display = args.hotkey.upper().replace("+", " + ")
    reset_display = args.reset_hotkey.upper().replace("+", " + ")
    platform_name = "Windows" if IS_WINDOWS else "Ubuntu"

    if IS_WINDOWS:
        clipboard_name = "Win32 API"
    else:
        clipboard_tool = _read_clipboard_command()
        clipboard_name = clipboard_tool[0] if clipboard_tool else "not found"

    typing_backend = "xdotool" if typer._use_xdotool else "pynput"

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print(f"  ║          🚀  AUTO-TYPER  ({platform_name:<10s})       ║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  Start/Stop : {hotkey_display:<33s} ║")
    print(f"  ║  Reset      : {reset_display:<33s} ║")
    speed_display = typer._speed_label()
    print(f"  ║  Speed      : {speed_display:<33s} ║")
    print(f"  ║  Indent     : {args.indent_mode:<33s} ║")
    print(f"  ║  Clipboard  : {clipboard_name:<33s} ║")
    print(f"  ║  Typing     : {typing_backend:<33s} ║")
    if not IS_WINDOWS:
        print(f"  ║  DISPLAY    : {os.environ.get('DISPLAY', ''):<33s} ║")
    print("  ║                                              ║")
    print("  ║  1. Copy text with Ctrl+C                    ║")
    print("  ║  2. Click where you want to type             ║")
    print(f"  ║  3. {hotkey_display} = start / resume          ║")
    print(f"  ║  4. {hotkey_display} while typing = stop       ║")
    print("  ║     after current line finishes              ║")
    print(f"  ║  5. {reset_display} = reset to beginning      ║")
    print("  ║                                              ║")
    print("  ║  Ctrl+C here to quit                         ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  Listening for {hotkey_str} and {reset_hotkey_str} …")
    print()

    try:
        with keyboard.GlobalHotKeys(hotkeys) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n  👋 Auto-Typer stopped. Bye!")
        sys.exit(0)


if __name__ == "__main__":
    main()