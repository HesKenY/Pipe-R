"""
halo_keylog.py — KenAI-native keystroke + mouse button capture

Watches Ken play Halo 2 MCC. Appends one JSONL row per event
(key down/up, mouse button down/up) to:

    brain/corpus/halo_tools_logs/halo-keylog.jsonl

Only fires while Halo has foreground focus — walks away from
your desktop typing the moment you alt-tab to Chrome. Uses
the `keyboard` and `mouse` pip modules (low-level hooks, so
the capture works regardless of which window has focus — BUT
we filter by foreground window title to only keep Halo events).

Stop by:
  - dropping KEYLOG_STOP.flag next to the script
  - OR killing the python process (taskkill /IM python.exe /F)

Usage:
    python halo_keylog.py                        # default path
    python halo_keylog.py --out path/to/log.jsonl
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

try:
    import keyboard as kb
except ImportError:
    print("keyboard module required: pip install keyboard")
    sys.exit(2)

try:
    import mouse as ms
except ImportError:
    print("mouse module required: pip install mouse")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "brain" / "corpus" / "halo_tools_logs" / "halo-keylog.jsonl"
STOP_FLAG = HERE / "KEYLOG_STOP.flag"

# ── Windows foreground-window helper ─────────────────────
_user32 = ctypes.windll.user32
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int

# DPI aware — otherwise window title lookups can lag on 4K/ultrawide
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def halo_is_foreground() -> bool:
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        n = _user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        _user32.GetWindowTextW(hwnd, buf, n + 1)
        title = (buf.value or "").lower()
        return any(k in title for k in ("halo", "mcc", "master chief"))
    except Exception:
        return False


class Keylogger:
    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.out_path, "a", encoding="utf-8", buffering=1)
        self._start_ts = time.time()
        self._events = 0
        self._dropped_off_halo = 0

    def _write(self, kind: str, **fields) -> None:
        if not halo_is_foreground():
            self._dropped_off_halo += 1
            return
        row = {
            "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "kind": kind,
            **fields,
        }
        self._fh.write(json.dumps(row, default=str) + "\n")
        self._events += 1

    def _on_keyboard(self, event) -> None:
        self._write(
            kind="key",
            name=getattr(event, "name", None),
            scan=getattr(event, "scan_code", None),
            dir=getattr(event, "event_type", None),  # "down" | "up"
        )

    def _on_mouse(self, event) -> None:
        cls = type(event).__name__
        if cls == "ButtonEvent":
            self._write(
                kind="mouse_btn",
                button=getattr(event, "button", None),
                dir=getattr(event, "event_type", None),  # "down" | "up" | "double"
            )
        elif cls == "MoveEvent":
            # skip — motion is too noisy, only on-click snapshots matter
            pass
        elif cls == "WheelEvent":
            self._write(
                kind="mouse_wheel",
                delta=getattr(event, "delta", 0),
            )

    def run(self) -> None:
        kb.hook(self._on_keyboard)
        ms.hook(self._on_mouse)
        print(f"[halo_keylog] running, writing to {self.out_path}")
        print(f"[halo_keylog] drop {STOP_FLAG.name} next to this script to stop")
        try:
            while True:
                if STOP_FLAG.exists():
                    print("[halo_keylog] STOP flag seen, exiting")
                    try: STOP_FLAG.unlink()
                    except Exception: pass
                    break
                time.sleep(0.25)
        except KeyboardInterrupt:
            print("[halo_keylog] Ctrl+C")
        finally:
            try: kb.unhook_all()
            except Exception: pass
            try: ms.unhook_all()
            except Exception: pass
            self._fh.close()
            elapsed = time.time() - self._start_ts
            print(f"[halo_keylog] stopped — {self._events} events in {elapsed:.1f}s "
                  f"({self._dropped_off_halo} dropped while not in halo)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out_path = Path(args.out).resolve()
    Keylogger(out_path).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
