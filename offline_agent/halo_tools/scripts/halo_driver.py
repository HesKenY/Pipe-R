"""
halo_driver.py — KenAI-native gameplay driver (overnight learn mode)

Reads the latest vision read from halo-vision.jsonl + uses a
simple policy to pick a movement action, then executes it via
SendInput keyboard + mouse. Runs alongside ken_aimbot.py
(aimbot handles shooting, driver handles movement).

Policy is intentionally dumb-but-safe for V1:
  - situation == combat       → hold W for 400ms + fire once
  - situation == exploration  → forward burst 600ms, occasional
                                 strafe for variety
  - situation == death_screen → noop (wait for respawn)
  - situation == menu/cutscene → noop
  - situation == unknown      → forward burst
  - every N ticks, a random small action so the model sees
    variety in the training corpus

Key safety rules:
  1. Foreground guard — any key/mouse send is a no-op if Halo
     isn't the focused window. Alt-tab = instant pause.
  2. Stop flag — drop DRIVER_STOP.flag next to this script
     and the loop exits within 500ms.
  3. Rate limit — one action per tick (default 800ms), never
     mashing.
  4. Reload auto-fire — press R every 90 seconds as a cheap
     "don't get caught empty" heuristic.

Logs every action to brain/corpus/halo_tools_logs/halo-driver.jsonl.

Usage:
    python halo_driver.py
    python halo_driver.py --tick 1200 --fire-rate 0.3
"""

from __future__ import annotations

import argparse
import ctypes
import json
import random
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "brain" / "corpus" / "halo_tools_logs" / "halo-driver.jsonl"
VISION_LOG = HERE.parent.parent / "brain" / "corpus" / "halo_tools_logs" / "halo-vision.jsonl"
STOP_FLAG = HERE / "DRIVER_STOP.flag"

# ── DPI aware ────────────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ── SendInput scaffolding ───────────────────────────────
# Same struct layout as ken_aimbot.py so both share a mouse
# pipe and Halo's Raw Input sees consistent deltas.

INPUT_KEYBOARD         = 1
INPUT_MOUSE            = 0
KEYEVENTF_KEYUP        = 0x0002
KEYEVENTF_SCANCODE     = 0x0008
MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004

ULONG_PTR = ctypes.c_ulong if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("u", _INPUT_UNION),
    ]


_user32 = ctypes.windll.user32
_user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_user32.SendInput.restype = wintypes.UINT
_SIZEOF_INPUT = ctypes.sizeof(INPUT)

# DirectInput scan codes — these reach games that ignore
# virtual-key based SendInput.
SCAN = {
    "w": 0x11, "a": 0x1E, "s": 0x1F, "d": 0x20,
    "space": 0x39, "shift_l": 0x2A, "ctrl_l": 0x1D,
    "e": 0x12, "r": 0x13, "q": 0x10, "f": 0x21,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "tab": 0x0F, "esc": 0x01,
}


def _send_key(scan: int, up: bool) -> None:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0
    inp.u.ki.wScan = scan
    inp.u.ki.dwFlags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    inp.u.ki.time = 0
    inp.u.ki.dwExtraInfo = 0
    _user32.SendInput(1, ctypes.byref(inp), _SIZEOF_INPUT)


def _send_mouse_btn(flag: int) -> None:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dx = 0
    inp.u.mi.dy = 0
    inp.u.mi.mouseData = 0
    inp.u.mi.dwFlags = flag
    inp.u.mi.time = 0
    inp.u.mi.dwExtraInfo = 0
    _user32.SendInput(1, ctypes.byref(inp), _SIZEOF_INPUT)


# ── Foreground guard ────────────────────────────────────
_user32.GetForegroundWindow.restype = wintypes.HWND


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


def press_key(key: str, hold_ms: int = 200) -> None:
    """Hold a key for hold_ms then release. Foreground-guarded."""
    if not halo_is_foreground():
        return
    scan = SCAN.get(key)
    if not scan:
        return
    _send_key(scan, up=False)
    time.sleep(hold_ms / 1000.0)
    _send_key(scan, up=True)


def fire_once(hold_ms: int = 80) -> None:
    if not halo_is_foreground():
        return
    _send_mouse_btn(MOUSEEVENTF_LEFTDOWN)
    time.sleep(hold_ms / 1000.0)
    _send_mouse_btn(MOUSEEVENTF_LEFTUP)


def _send_mouse_move(dx: int, dy: int) -> None:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dx = int(dx)
    inp.u.mi.dy = int(dy)
    inp.u.mi.mouseData = 0
    inp.u.mi.dwFlags = MOUSEEVENTF_MOVE
    inp.u.mi.time = 0
    inp.u.mi.dwExtraInfo = 0
    _user32.SendInput(1, ctypes.byref(inp), _SIZEOF_INPUT)


def look(dx: int, dy: int, smoothing: int = 5) -> None:
    """
    Mouse-look via relative SendInput. Halo takes the delta
    through Raw Input. Split into mini-steps so each one is
    sampled. Foreground-guarded.
    """
    if not halo_is_foreground():
        return
    step_x = dx // smoothing
    step_y = dy // smoothing
    rem_x = dx - step_x * smoothing
    rem_y = dy - step_y * smoothing
    for i in range(smoothing):
        rx = step_x + (rem_x if i == smoothing - 1 else 0)
        ry = step_y + (rem_y if i == smoothing - 1 else 0)
        _send_mouse_move(rx, ry)
        time.sleep(0.008)


# ── Vision log tail ──────────────────────────────────────

def read_latest_vision() -> dict | None:
    """Return the parsed row from the last line of halo-vision.jsonl."""
    if not VISION_LOG.exists():
        return None
    try:
        with VISION_LOG.open("rb") as f:
            # Tail the last ~4KB to avoid reading huge files
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", errors="ignore")
        lines = [l for l in tail.splitlines() if l.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


# ── Policy ───────────────────────────────────────────────

# Exploration pattern — 20-step loop that mixes movement,
# look, jump, crouch, fire, and reload. When vision is stale
# or says "unknown", the driver cycles through this pattern
# so the character never gets stuck walking into a wall.
EXPLORATION_PATTERN = [
    "forward", "forward", "look_right", "forward",
    "strafe_right", "fire", "forward", "look_left",
    "forward", "strafe_left", "jump", "forward",
    "fire", "look_down", "forward", "forward",
    "crouch", "look_up", "forward", "reload",
]

COMBAT_PATTERN = [
    "fire", "strafe_left", "fire", "forward",
    "fire", "strafe_right", "fire", "look_right",
    "fire", "back", "fire", "look_left",
]


def pick_action(vision_row: dict | None, tick_count: int) -> tuple[str, dict]:
    """
    Return (action, metadata). Actions:
      forward / back / strafe_left / strafe_right /
      jump / crouch / reload / fire /
      look_left / look_right / look_up / look_down /
      noop

    Policy priority:
      1. If vision says mission_complete / death / menu → noop
      2. If vision says combat → combat pattern (fire heavy +
         strafe + look sweeps)
      3. Else (exploration, unknown, stale) → exploration pattern
         (rotating mix so we never get stuck walking forward)
      4. Every N ticks inject a random "stuck breaker" —
         jump + look_right + fire burst.
    """
    ctx = {"tick": tick_count}

    situation = "unknown"
    vision_action = None
    if vision_row:
        parsed = vision_row.get("parsed") or {}
        situation = (parsed.get("situation") or "unknown").lower()
        vision_action = (parsed.get("action") or "").lower()
        ctx["situation"] = situation
        ctx["vision_action"] = vision_action

    # Hard noop cases
    if situation in ("death_screen", "menu", "cutscene", "mission_complete"):
        return "noop", ctx

    # Combat — use the combat pattern + occasional vision override
    if situation == "combat":
        if vision_action in ("fire", "ads"):
            return "fire", ctx
        if vision_action in ("move_back", "back"):
            return "back", ctx
        action = COMBAT_PATTERN[tick_count % len(COMBAT_PATTERN)]
        return action, ctx

    # Stuck breaker every ~25 ticks — random burst to unwedge
    if tick_count > 0 and tick_count % 25 == 0:
        breaker = random.choice([
            "jump", "look_right", "look_left", "strafe_left",
            "strafe_right", "fire",
        ])
        ctx["breaker"] = True
        return breaker, ctx

    # Exploration / unknown — cycle the pattern
    action = EXPLORATION_PATTERN[tick_count % len(EXPLORATION_PATTERN)]
    return action, ctx


ACTION_IMPL = {
    "forward":     lambda: press_key("w", 520),
    "back":        lambda: press_key("s", 380),
    "strafe_left": lambda: press_key("a", 360),
    "strafe_right":lambda: press_key("d", 360),
    "jump":        lambda: press_key("space", 90),
    "reload":      lambda: press_key("r", 120),
    "crouch":      lambda: press_key("ctrl_l", 140),
    "fire":        lambda: fire_once(70),
    "noop":        lambda: None,
    # Mouse-look — relative deltas. Halo takes these through
    # Raw Input. Values are in raw mouse units, which Windows
    # scales by the game's sensitivity curve.
    "look_left":   lambda: look(-220, 0),
    "look_right":  lambda: look(220, 0),
    "look_up":     lambda: look(0, -140),
    "look_down":   lambda: look(0, 140),
}


# ── Main loop ────────────────────────────────────────────

def run(tick_ms: int, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(out_path, "a", encoding="utf-8", buffering=1)

    print(f"[halo_driver] tick={tick_ms}ms, writing to {out_path}")
    print(f"[halo_driver] drop {STOP_FLAG.name} to stop")

    tick_count = 0
    last_reload = time.time()
    start_ts = time.time()
    try:
        while True:
            if STOP_FLAG.exists():
                print("[halo_driver] STOP flag seen")
                try: STOP_FLAG.unlink()
                except Exception: pass
                break

            if not halo_is_foreground():
                time.sleep(0.4)
                continue

            vision = read_latest_vision()
            action, ctx = pick_action(vision, tick_count)

            # Cheap safety reload every 90s regardless
            if time.time() - last_reload > 90:
                action = "reload"
                last_reload = time.time()
                ctx["forced_reload"] = True

            impl = ACTION_IMPL.get(action, ACTION_IMPL["noop"])
            t_before = time.time()
            try:
                impl()
                ok = True
                err = None
            except Exception as e:
                ok = False
                err = str(e)

            row = {
                "at":      datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "tick":    tick_count,
                "action":  action,
                "ok":      ok,
                "err":     err,
                "elapsed_ms": int((time.time() - t_before) * 1000),
                "ctx":     ctx,
            }
            fh.write(json.dumps(row, default=str) + "\n")

            if tick_count % 10 == 0:
                print(f"[halo_driver] tick={tick_count} action={action} "
                      f"situation={ctx.get('situation', '-')}")

            tick_count += 1
            time.sleep(tick_ms / 1000.0)
    except KeyboardInterrupt:
        print("[halo_driver] Ctrl+C")
    finally:
        fh.close()
        elapsed = time.time() - start_ts
        print(f"[halo_driver] stopped — {tick_count} ticks in {elapsed:.1f}s")
    return 0


SINGLETON_LOCK = HERE / "halo_driver.lock"


def _claim_singleton() -> bool:
    """Prevent double-launches. Writes our PID to a lock file;
    if the file already exists with a live PID, bail out."""
    if SINGLETON_LOCK.exists():
        try:
            other_pid = int(SINGLETON_LOCK.read_text(encoding="utf-8").strip() or "0")
            if other_pid > 0:
                # Probe if that PID is still alive
                OPEN = ctypes.windll.kernel32.OpenProcess
                CLOSE = ctypes.windll.kernel32.CloseHandle
                h = OPEN(0x0400, False, other_pid)
                if h:
                    CLOSE(h)
                    print(f"[halo_driver] another instance already running (pid {other_pid})")
                    return False
        except Exception:
            pass
    try:
        import os
        SINGLETON_LOCK.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    return True


def _release_singleton() -> None:
    try:
        SINGLETON_LOCK.unlink()
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick", type=int, default=800, help="tick interval in ms")
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    args = ap.parse_args()
    if not _claim_singleton():
        return 1
    try:
        return run(args.tick, Path(args.out).resolve())
    finally:
        _release_singleton()


if __name__ == "__main__":
    sys.exit(main())
