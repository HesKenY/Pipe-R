"""
Factorio actuator — fires one action from KenAI's vocabulary.

Same architecture as halo_do.py. Takes an action name + optional
duration, executes the keypress/mouse action, returns confirmation.

Usage:
    python factorio_do.py <action> [duration_ms]

Factorio action vocabulary:
    Movement:    move_north, move_south, move_east, move_west
    Camera:      zoom_in, zoom_out
    Build:       place, remove, rotate, pipette, copy, paste
    Interact:    open_inventory, open_map, open_tech, open_production
    Combat:      shoot, throw_capsule
    Control:     confirm, cancel, toggle_alt, pause
    Crafting:    craft_1, craft_5, craft_all
    Quick:       hotbar_1..hotbar_10
    Special:     noop
"""

import json
import sys
import time

try:
    import pydirectinput as pdi
    HAS_PDI = True
except ImportError:
    HAS_PDI = False

try:
    import pyautogui
    HAS_PAG = True
    pyautogui.FAILSAFE = False
except ImportError:
    HAS_PAG = False


# key = hold for duration
KEY_MAP = {
    "move_north":  ("hold", "w"),
    "move_south":  ("hold", "s"),
    "move_east":   ("hold", "d"),
    "move_west":   ("hold", "a"),
    "rotate":      ("tap", "r"),
    "pipette":     ("tap", "q"),
    "open_inventory": ("tap", "e"),
    "open_map":    ("tap", "m"),
    "open_tech":   ("tap", "t"),
    "toggle_alt":  ("tap", "alt"),
    "confirm":     ("tap", "return"),
    "cancel":      ("tap", "escape"),
    "pause":       ("tap", "space"),
    "hotbar_1":    ("tap", "1"),
    "hotbar_2":    ("tap", "2"),
    "hotbar_3":    ("tap", "3"),
    "hotbar_4":    ("tap", "4"),
    "hotbar_5":    ("tap", "5"),
    "hotbar_6":    ("tap", "6"),
    "hotbar_7":    ("tap", "7"),
    "hotbar_8":    ("tap", "8"),
    "hotbar_9":    ("tap", "9"),
    "hotbar_10":   ("tap", "0"),
}

MOUSE_MAP = {
    "place":       ("click", "left"),
    "remove":      ("click", "right"),
    "shoot":       ("click", "left"),  # with gun equipped
    "zoom_in":     ("scroll", 3),
    "zoom_out":    ("scroll", -3),
}


def do_key_hold(key, duration_s):
    if HAS_PDI:
        pdi.keyDown(key)
        time.sleep(max(duration_s, 0.12))
        pdi.keyUp(key)
        return "pdi:hold"
    if HAS_PAG:
        pyautogui.keyDown(key)
        time.sleep(max(duration_s, 0.12))
        pyautogui.keyUp(key)
        return "pag:hold"
    return "none"


def do_key_tap(key):
    if HAS_PDI:
        pdi.press(key)
        return "pdi:tap"
    if HAS_PAG:
        pyautogui.press(key)
        return "pag:tap"
    return "none"


def do_mouse_click(button, duration_s):
    if HAS_PDI:
        pdi.mouseDown(button=button)
        time.sleep(max(duration_s, 0.08))
        pdi.mouseUp(button=button)
        return "pdi:click"
    if HAS_PAG:
        pyautogui.mouseDown(button=button)
        time.sleep(max(duration_s, 0.08))
        pyautogui.mouseUp(button=button)
        return "pag:click"
    return "none"


def do_scroll(amount):
    if HAS_PAG:
        pyautogui.scroll(amount)
        return "pag:scroll"
    return "none"


def fire(action, duration_ms):
    duration_ms = max(0, min(2000, int(duration_ms)))
    duration_s = duration_ms / 1000.0

    if action in KEY_MAP:
        kind, key = KEY_MAP[action]
        if kind == "hold":
            backend = do_key_hold(key, duration_s)
        else:
            backend = do_key_tap(key)
        return backend + ":" + key

    if action in MOUSE_MAP:
        spec = MOUSE_MAP[action]
        if spec[0] == "click":
            return do_mouse_click(spec[1], duration_s) + ":" + spec[1]
        if spec[0] == "scroll":
            return do_scroll(spec[1])

    if action == "noop":
        time.sleep(0.05)
        return "noop"

    return "unknown:" + action


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: factorio_do.py <action> [duration_ms]\n")
        sys.exit(2)
    action = sys.argv[1].strip().lower()
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    detail = fire(action, duration)
    print(json.dumps({
        "action": action,
        "duration_ms": duration,
        "detail": detail,
        "backends": {"pdi": HAS_PDI, "pag": HAS_PAG},
    }))


if __name__ == "__main__":
    main()
