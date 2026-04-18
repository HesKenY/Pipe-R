"""
Pokemon Crystal actuator — GBC inputs via mGBA window.
A, B, Start, Select, D-pad (up/down/left/right).
"""
import json, sys, time
try:
    import pydirectinput as pdi; HAS_PDI = True
except: HAS_PDI = False
try:
    import pyautogui; HAS_PAG = True; pyautogui.FAILSAFE = False
except: HAS_PAG = False

KEYS = {
    "a": "x", "b": "z", "start": "return", "select": "backspace",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "l": "a", "r": "s",
}

def tap(key):
    k = KEYS.get(key, key)
    if HAS_PDI: pdi.press(k); return "pdi"
    if HAS_PAG: pyautogui.press(k); return "pag"
    return "none"

def hold(key, dur):
    k = KEYS.get(key, key)
    if HAS_PDI:
        pdi.keyDown(k); time.sleep(max(dur, 0.1)); pdi.keyUp(k); return "pdi"
    if HAS_PAG:
        pyautogui.keyDown(k); time.sleep(max(dur, 0.1)); pyautogui.keyUp(k); return "pag"
    return "none"

def fire(action, duration_ms=150):
    d = max(0, min(2000, int(duration_ms))) / 1000.0
    if action == "noop": time.sleep(0.05); return "noop"
    if action in ["up","down","left","right"]:
        return hold(action, d) + ":" + action
    return tap(action) + ":" + action

if __name__ == "__main__":
    action = sys.argv[1].strip().lower() if len(sys.argv) > 1 else "noop"
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    d = fire(action, dur)
    print(json.dumps({"action": action, "duration_ms": dur, "detail": d}))
