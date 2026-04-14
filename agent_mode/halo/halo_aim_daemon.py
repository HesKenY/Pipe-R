"""
Halo aim daemon — persistent Python process for 30fps aim scan.

Instead of spawning halo_do.py / aimbot.py fresh for every tick
(which costs ~80-120ms of Python startup + pyautogui/PIL import
per invocation, capping the loop at ~6-8 FPS in practice), this
module runs as a long-lived daemon that:

  1. Imports PIL, pyautogui, pydirectinput once at startup
  2. Loops forever, reading JSON commands from stdin
  3. Executes each command (scan, snap, fire, engage) in-process
  4. Writes one JSON result line to stdout per command
  5. Exits on EOF (when the Node side closes the pipe)

Node-side `agent.js` spawns this ONCE via child_process.spawn and
keeps the pipe open, sending commands at the target tick rate.
Typical in-process cycle (screenshot + flood-fill + snap + click)
is ~25-45ms — enough for ~25-40 FPS effective rate.

Command format (one JSON per line on stdin):

  {"op": "engage", "palette": "all", "minConfidence": 0.025,
   "burstSize": 2, "shotDelay": 80, "maxShots": 3}

Response format (one JSON per line on stdout):

  {"ok": true, "found": bool, "shots_fired": int, ...}

Commands supported:
  scan    — find_target only, no input
  snap    — find_target + snap mouse (no fire)
  fire    — find + snap + one click
  engage  — full burst loop with rescan between shots
  quit    — exit daemon
"""

import sys
import json
import time
import random
import ctypes

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except Exception as e:
    sys.stderr.write("pyautogui required: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image

# Share palette + find_target from aimbot.py — importing the
# module runs its top-level pyautogui check but we've already
# done that. Use the helpers directly.
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__
                 else __file__.rsplit('\\', 1)[0])
try:
    import aimbot as _a
except Exception as e:
    sys.stderr.write("aimbot import failed: " + str(e) + "\n")
    sys.exit(3)


MOUSEEVENTF_MOVE     = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004


def snap_mouse_fast(dx, dy, smoothing=4):
    step_x = int(dx / smoothing)
    step_y = int(dy / smoothing)
    rem_x = dx - step_x * smoothing
    rem_y = dy - step_y * smoothing
    for i in range(smoothing):
        rx = step_x + (rem_x if i == smoothing - 1 else 0)
        ry = step_y + (rem_y if i == smoothing - 1 else 0)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, rx, ry, 0, 0)
        # No sleep between sub-steps inside the daemon — 4 moves
        # back-to-back execute in microseconds.


def fire_shot_fast(hold_ms=70):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(hold_ms / 1000.0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def op_scan(palette):
    return _a.find_target(palette)


def op_snap(palette, min_conf):
    tgt = _a.find_target(palette)
    if tgt.get("found") and tgt.get("confidence", 0) >= min_conf:
        jx = random.randint(-3, 3)
        jy = random.randint(-3, 3)
        snap_mouse_fast(tgt["dx"] + jx, tgt["dy"] + jy)
        tgt["snapped"] = True
    return tgt


def op_fire(palette, min_conf):
    tgt = _a.find_target(palette)
    if tgt.get("found") and tgt.get("confidence", 0) >= min_conf:
        jx = random.randint(-3, 3)
        jy = random.randint(-3, 3)
        snap_mouse_fast(tgt["dx"] + jx, tgt["dy"] + jy)
        fire_shot_fast(hold_ms=60 + random.randint(0, 30))
        tgt["snapped"] = True
        tgt["fired"] = True
        tgt["shots_fired"] = 1
    else:
        tgt["shots_fired"] = 0
    return tgt


def op_engage(palette, min_conf, burst_size=3, shot_delay_ms=140, max_shots=5):
    first = _a.find_target(palette)
    if not first.get("found") or first.get("confidence", 0) < min_conf:
        first["shots_fired"] = 0
        first["engaged"] = False
        return first

    confidence = first["confidence"]
    if confidence < min_conf * 2:
        planned = 1
    elif confidence < min_conf * 4:
        planned = min(burst_size, 3)
    else:
        planned = min(max_shots, burst_size + 1)

    jx = random.randint(-4, 4)
    jy = random.randint(-4, 4)
    snap_mouse_fast(first["dx"] + jx, first["dy"] + jy, smoothing=4)
    time.sleep((20 + random.randint(0, 30)) / 1000.0)

    shots_fired = 0
    for i in range(planned):
        fire_shot_fast(hold_ms=55 + random.randint(0, 25))
        shots_fired += 1
        if i >= planned - 1:
            break
        jitter_delay = shot_delay_ms + random.randint(-25, 25)
        time.sleep(max(50, jitter_delay) / 1000.0)
        nxt = _a.find_target(palette)
        if not nxt.get("found") or nxt.get("confidence", 0) < min_conf * 0.6:
            break
        if abs(nxt.get("dx", 0)) > 30 or abs(nxt.get("dy", 0)) > 30:
            snap_mouse_fast(nxt["dx"], nxt["dy"], smoothing=3)
            time.sleep(0.005)

    report = dict(first)
    report["shots_fired"] = shots_fired
    report["planned_shots"] = planned
    report["engaged"] = True
    return report


def main():
    # Announce daemon is ready so Node knows when to start
    # piping commands.
    sys.stdout.write(json.dumps({"ok": True, "daemon": "ready", "pid": None}) + "\n")
    sys.stdout.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except Exception as e:
            sys.stdout.write(json.dumps({"ok": False, "error": "parse: " + str(e)}) + "\n")
            sys.stdout.flush()
            continue

        op = cmd.get("op", "scan")
        palette = cmd.get("palette", "all")
        min_conf = float(cmd.get("minConfidence", 0.04))
        t0 = time.time()
        try:
            if op == "scan":
                r = op_scan(palette)
            elif op == "snap":
                r = op_snap(palette, min_conf)
            elif op == "fire":
                r = op_fire(palette, min_conf)
            elif op == "engage":
                r = op_engage(palette, min_conf,
                              burst_size=int(cmd.get("burstSize", 3)),
                              shot_delay_ms=int(cmd.get("shotDelay", 140)),
                              max_shots=int(cmd.get("maxShots", 5)))
            elif op == "quit":
                sys.stdout.write(json.dumps({"ok": True, "bye": True}) + "\n")
                sys.stdout.flush()
                break
            else:
                r = {"ok": False, "error": "unknown op: " + op}
            if "ok" not in r:
                r["ok"] = True
            r["cycleMs"] = int((time.time() - t0) * 1000)
        except Exception as e:
            r = {"ok": False, "error": str(e), "cycleMs": int((time.time() - t0) * 1000)}

        sys.stdout.write(json.dumps(r) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
