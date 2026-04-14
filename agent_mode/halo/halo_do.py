"""
Halo MCC actuator — fires one action from the agent's vocabulary.

Usage:
    python halo_do.py <action> [duration_ms]

Input backends, in preference order:

    1. `keyboard` + `mouse` modules (low-level WH_KEYBOARD_LL /
        WH_MOUSE_LL hooks). Delivers to the game even when the
        game window is NOT focused. This is the "background
        control" path Ken asked for 2026-04-13.
    2. `pydirectinput` (SendInput with scan codes). Works for
        DirectInput games but ONLY when the game is focused.
    3. `pyautogui` (Windows message events). Pokemon for most
        games. Kept as last-ditch fallback.

Action vocabulary maps to Halo 2 / MCC PC default keybinds
(verified 2026-04-13 from halopedia.org/Control_schemes):

    move_fwd      → w          (hold)
    move_back     → s          (hold)
    strafe_left   → a          (hold)
    strafe_right  → d          (hold)
    jump          → space      (tap)
    crouch        → left_ctrl  (hold)
    sprint        → left_shift (hold)   [Reach/4/5 only; noop in H1/H2]
    fire          → lmb        (click)
    ads           → rmb        (click)
    reload        → r          (tap)
    interact      → e          (tap)
    grenade       → f          (tap)     [MCC default — not G]
    melee         → q          (tap)     [MCC default — not V/F]
    weapon_slot_1 → 1          (tap)
    switch_grenade→ 2          (tap)
    flashlight    → 4          (tap)
    dual_wield    → c          (tap)
    scoreboard    → tab        (tap)
    pause         → esc        (tap)
    look_left     → mouse rel (-220, 0)
    look_right    → mouse rel (+220, 0)
    look_up       → mouse rel (0, -140)
    look_down     → mouse rel (0, +140)
    noop          → nothing

Safety: 150ms default, 1500ms hold ceiling. Emits one JSON line.
"""

import sys
import json
import time

# Backend selection — try the background-capable modules first,
# then DirectInput, then fall back to pyautogui as last resort.
# HAS_KB is true when the low-level keyboard hook is available,
# meaning input reaches the game regardless of window focus.
try:
    import keyboard as _kb
    HAS_KB = True
except Exception:
    _kb = None
    HAS_KB = False

try:
    import mouse as _ms
    HAS_MS = True
except Exception:
    _ms = None
    HAS_MS = False

try:
    import pydirectinput as pdi
    pdi.FAILSAFE = False
    pdi.PAUSE = 0
    HAS_PDI = True
except Exception:
    pdi = None
    HAS_PDI = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    HAS_PAG = True
except Exception:
    pyautogui = None
    HAS_PAG = False


# Halo 2 MCC PC default keymap (halopedia.org 2026-04-13).
# (kind, key) — "hold" keys are held for the requested duration,
# "tap" keys fire once.
KEY_MAP = {
    "move_fwd":      ("hold", "w"),
    "move_back":     ("hold", "s"),
    "strafe_left":   ("hold", "a"),
    "strafe_right":  ("hold", "d"),
    "jump":          ("tap",  "space"),
    "crouch":        ("hold", "left ctrl"),
    "sprint":        ("hold", "left shift"),
    "reload":        ("tap",  "r"),
    "interact":      ("tap",  "e"),
    "grenade":       ("tap",  "f"),
    "melee":         ("tap",  "q"),
    "weapon_slot_1": ("tap",  "1"),
    "switch_grenade":("tap",  "2"),
    "flashlight":    ("tap",  "4"),
    "dual_wield":    ("tap",  "c"),
    "scoreboard":    ("tap",  "tab"),
    "pause":         ("tap",  "esc"),
}

# pydirectinput + pyautogui use different key name conventions
# (no space between modifier and key). Translate for fallbacks.
PDI_KEY_TRANSLATE = {
    "left ctrl": "ctrl",
    "left shift": "shift",
}
def _pdi_key(k): return PDI_KEY_TRANSLATE.get(k, k)

MOUSE_MAP = {
    "fire":       ("click", "left"),
    "ads":        ("click", "right"),
    "look_left":  ("rel", -220, 0),
    "look_right": ("rel",  220, 0),
    "look_up":    ("rel",  0, -140),
    "look_down":  ("rel",  0,  140),
}


def _do_key_hold(key, duration_s):
    """Press + hold + release. pydirectinput is known-good for
    DirectInput games (Halo MCC); it goes first when available.
    keyboard module second, pyautogui last."""
    if HAS_PDI:
        pdi.keyDown(_pdi_key(key))
        time.sleep(duration_s if duration_s > 0 else 0.12)
        pdi.keyUp(_pdi_key(key))
        return "pdi:hold"
    if HAS_KB:
        _kb.press(key)
        time.sleep(duration_s if duration_s > 0 else 0.12)
        _kb.release(key)
        return "kb:hold"
    if HAS_PAG:
        pyautogui.keyDown(_pdi_key(key))
        time.sleep(duration_s if duration_s > 0 else 0.12)
        pyautogui.keyUp(_pdi_key(key))
        return "pag:hold"
    return "none:hold"

def _do_key_tap(key):
    if HAS_PDI:
        pdi.press(_pdi_key(key))
        return "pdi:tap"
    if HAS_KB:
        _kb.send(key)
        return "kb:tap"
    if HAS_PAG:
        pyautogui.press(_pdi_key(key))
        return "pag:tap"
    return "none:tap"

def _do_mouse_click(button, duration_s):
    if HAS_PDI:
        pdi.mouseDown(button=button)
        time.sleep(duration_s if duration_s > 0 else 0.08)
        pdi.mouseUp(button=button)
        return "pdi:click"
    if HAS_MS:
        _ms.press(button)
        time.sleep(duration_s if duration_s > 0 else 0.08)
        _ms.release(button)
        return "ms:click"
    if HAS_PAG:
        pyautogui.mouseDown(button=button)
        time.sleep(duration_s if duration_s > 0 else 0.08)
        pyautogui.mouseUp(button=button)
        return "pag:click"
    return "none:click"

def _do_mouse_rel(dx, dy):
    """Relative mouse for camera look. Halo MCC reads raw mouse
    deltas. The lowest-level path is ctypes mouse_event with
    MOUSEEVENTF_MOVE (flag 0x0001) — SendInput's underlying
    primitive. That goes first. Then pydirectinput.moveRel,
    then the mouse module's relative move, then pyautogui."""
    try:
        import ctypes
        MOUSEEVENTF_MOVE = 0x0001
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
        return "ctypes:rel"
    except Exception:
        pass
    if HAS_PDI:
        try:
            pdi.moveRel(dx, dy, relative=True)
            return "pdi:rel"
        except Exception:
            pass
    if HAS_MS:
        try:
            _ms.move(dx, dy, absolute=False, duration=0)
            return "ms:rel"
        except Exception:
            pass
    if HAS_PAG:
        pyautogui.moveRel(dx, dy, duration=0.08)
        return "pag:rel"
    return "none:rel"


def fire(action, duration_ms):
    duration_ms = max(0, min(1500, int(duration_ms)))
    duration_s = duration_ms / 1000.0

    if action in KEY_MAP:
        kind, key = KEY_MAP[action]
        if kind == "hold":
            backend = _do_key_hold(key, duration_s)
        else:
            backend = _do_key_tap(key)
        return backend + ":" + key

    if action in MOUSE_MAP:
        spec = MOUSE_MAP[action]
        if spec[0] == "click":
            backend = _do_mouse_click(spec[1], duration_s)
            return backend + ":" + spec[1]
        if spec[0] == "rel":
            backend = _do_mouse_rel(spec[1], spec[2])
            return backend + ":{},{}".format(spec[1], spec[2])

    if action == "noop":
        time.sleep(0.05)
        return "noop"

    return "unknown:" + action


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: halo_do.py <action> [duration_ms]\n")
        sys.exit(2)
    action = sys.argv[1].strip().lower()
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    detail = fire(action, duration)
    sys.stdout.write(json.dumps({
        "action": action,
        "duration_ms": duration,
        "detail": detail,
        "backends": {
            "keyboard": HAS_KB,
            "mouse":    HAS_MS,
            "pdi":      HAS_PDI,
            "pyautogui":HAS_PAG,
        },
    }) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
