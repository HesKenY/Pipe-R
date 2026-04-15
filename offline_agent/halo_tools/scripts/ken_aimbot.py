"""
KEN AIMBOT — standalone, no dependencies on the project tree.

Double-click KEN_AIMBOT.bat to launch. Drop a file named
AIMBOT_STOP.flag on the desktop to stop. Press F10 in-game
to toggle pause/resume (requires `keyboard` module).

What it does:
  - Screenshots center 34% of the screen every ~100ms
  - Floods fills for red / purple / orange "enemy outline" colors
  - Picks the biggest blob weighted by distance from crosshair
  - Aims at top 8% of the blob's bounding box (headshot bias)
  - Snaps the mouse there with ±4px human jitter
  - Fires LMB burst (3 shots) with jittered timing
  - Repeats

Requires: pyautogui, PIL (comes with pyautogui). Optional:
`keyboard` for F10 pause toggle (falls back to stop-flag only).

Halo MCC must be the focused window for keyboard/mouse input
to register — that's a Windows SendInput limitation, not an
aimbot flaw. Do not alt-tab away while running.
"""

import sys
import time
import random
import ctypes
import json
from ctypes import wintypes
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except Exception as e:
    print("pyautogui required: " + str(e))
    sys.exit(2)

from PIL import Image

try:
    import keyboard as _kb
    HAS_KB = True
except Exception:
    _kb = None
    HAS_KB = False

# ── DPI awareness — required on 4K/ultrawide so mouse deltas
# aren't silently scaled by Windows Pointer Precision ────
try:
    # Per-monitor v2 is the best mode on Win10 1703+
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ── Config — aggressive headhunting profile ──────────────
CENTER_FRAC       = 0.42    # wider field of view
TARGET_WIDTH      = 480     # downsample width for scanning speed
MIN_BBOX          = 6       # min bbox side (downsampled pixels)
MIN_BLOB_PIXELS   = 12      # min pixel count to count as blob
MIN_CONFIDENCE    = 0.015   # 0-1, lower = fires more often
SCAN_INTERVAL_MS  = 60      # cycle time
BURST_SIZE        = 5       # shots per engagement
SHOT_DELAY_MS     = 85      # gap between burst shots
SHOT_HOLD_MS      = 55      # LMB down duration
HEAD_BIAS_FRAC    = 0.04    # aim at top N% of bbox — hard head bias
HUD_TOP_SKIP      = 0.10    # skip top 10% of crop
HUD_BOTTOM_SKIP   = 0.85    # skip everything below 85%

# Palette — (rmin, rmax, gmin, gmax, bmin, bmax). Edit to
# catch different enemy outline colors.
PALETTE = [
    ("red",        150, 255,   0, 100,   0, 100),
    ("bright_red", 200, 255,   0,  80,   0,  80),
    ("purple",     120, 220,   0, 100, 120, 255),
    ("orange",     200, 255, 100, 180,   0,  80),
]

STOP_FLAG = Path(__file__).resolve().parent / "AIMBOT_STOP.flag"
PAUSE_HOTKEY = "f10"

# Every scan + every engagement lands in this file as one JSONL
# line. Used for post-run analysis + future tuning. Capped so
# the file doesn't grow unbounded during long sessions.
LOG_FILE = Path(__file__).resolve().parent / "aimbot.log.jsonl"
LOG_MAX_LINES = 50000  # keep ~50k rows (roughly 8-20 MB)


def log_event(event):
    """Append one JSONL line to the aimbot log. Best-effort —
    any write failure is swallowed so the hot loop never dies
    because of a log problem."""
    try:
        event['at'] = datetime.now(timezone.utc).isoformat()
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')
    except Exception:
        pass


def maybe_trim_log():
    """Roll the log if it gets too big. Called once per run."""
    try:
        if not LOG_FILE.exists():
            return
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        if len(lines) > LOG_MAX_LINES:
            keep = lines[-(LOG_MAX_LINES // 2):]
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(keep)
    except Exception:
        pass


# ── Mouse primitives via SendInput ────────────────────────
# mouse_event is deprecated and some games that listen via
# Raw Input ignore it. SendInput is what every modern aimbot
# uses because it routes through the same input queue as a
# real USB mouse — Halo MCC's Raw Input pipe picks it up.
#
# INPUT struct layout from winuser.h. We only care about
# mouse input so the union is padded with a MOUSEINPUT + a
# bit of slack for KEYBDINPUT that we don't use.

MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_ABSOLUTE   = 0x8000  # not used for game aim
INPUT_MOUSE            = 0

ULONG_PTR = ctypes.c_ulong if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("mi",   MOUSEINPUT),  # direct field is fine since we only do mouse
        ("_pad", ctypes.c_ulong * 4),  # pad out to full INPUT size on x64
    ]

_user32 = ctypes.windll.user32
_user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_user32.SendInput.restype  = wintypes.UINT
_SIZEOF_INPUT = ctypes.sizeof(INPUT)


def _send_mouse(dx: int, dy: int, flags: int) -> None:
    """Send one mouse event via SendInput. Relative coords."""
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = int(dx)
    inp.mi.dy = int(dy)
    inp.mi.mouseData = 0
    inp.mi.dwFlags = flags
    inp.mi.time = 0
    inp.mi.dwExtraInfo = 0
    _user32.SendInput(1, ctypes.byref(inp), _SIZEOF_INPUT)


def _halo_is_foreground() -> bool:
    """Cheap check — are we aiming at the Halo window?
    Returns True if foreground window title contains 'Halo'
    or 'MCC' or 'Master Chief'. False means we're alt-tabbed
    away and should skip this cycle (no point snapping the
    OS cursor onto nothing)."""
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        length = _user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        title = (buf.value or "").lower()
        return any(k in title for k in ("halo", "mcc", "master chief"))
    except Exception:
        return True  # fail open — don't block aim on a probe error


def snap_mouse(dx, dy, smoothing=4):
    """
    Split the move into `smoothing` mini-steps so Halo's Raw
    Input sampler catches each one. With SendInput the delta
    is in raw mouse units, NOT screen pixels — Windows still
    scales by the mouse driver's sensitivity curve.

    Skip entirely if Halo doesn't have foreground focus — the
    mouse would move on the desktop for no reason.
    """
    if not _halo_is_foreground():
        return
    dx = int(dx)
    dy = int(dy)
    if dx == 0 and dy == 0:
        return
    step_x = dx // smoothing
    step_y = dy // smoothing
    rem_x = dx - step_x * smoothing
    rem_y = dy - step_y * smoothing
    for i in range(smoothing):
        rx = step_x + (rem_x if i == smoothing - 1 else 0)
        ry = step_y + (rem_y if i == smoothing - 1 else 0)
        _send_mouse(rx, ry, MOUSEEVENTF_MOVE)
        time.sleep(0.006)


def fire_shot(hold_ms=70):
    if not _halo_is_foreground():
        return
    _send_mouse(0, 0, MOUSEEVENTF_LEFTDOWN)
    time.sleep(hold_ms / 1000.0)
    _send_mouse(0, 0, MOUSEEVENTF_LEFTUP)


# ── Pixel matching + flood fill ──────────────────────────
def pixel_matches(r, g, b):
    for _, rmin, rmax, gmin, gmax, bmin, bmax in PALETTE:
        if rmin <= r <= rmax and gmin <= g <= gmax and bmin <= b <= bmax:
            return True
    return False

def cluster_blobs(mask, w, h):
    visited = bytearray(w * h)
    blobs = []
    for start_y in range(h):
        row = start_y * w
        for start_x in range(w):
            idx = row + start_x
            if visited[idx] or not mask[idx]:
                continue
            stack = [(start_x, start_y)]
            visited[idx] = 1
            sum_x = 0; sum_y = 0; count = 0
            bx0, by0, bx1, by1 = start_x, start_y, start_x, start_y
            while stack:
                x, y = stack.pop()
                sum_x += x; sum_y += y; count += 1
                if x < bx0: bx0 = x
                if x > bx1: bx1 = x
                if y < by0: by0 = y
                if y > by1: by1 = y
                for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if not visited[nidx] and mask[nidx]:
                            visited[nidx] = 1
                            stack.append((nx, ny))
            if count >= MIN_BLOB_PIXELS:
                blobs.append({
                    "pixels": count,
                    "bbox": (bx0, by0, bx1, by1),
                    "centroid": (sum_x / count, sum_y / count),
                })
    return blobs


# ── Target finder ────────────────────────────────────────
def find_target():
    shot = pyautogui.screenshot()
    w, h = shot.size
    crop_w = int(w * CENTER_FRAC)
    crop_h = int(h * CENTER_FRAC)
    cx = w // 2
    cy = h // 2
    left = cx - crop_w // 2
    top  = cy - crop_h // 2
    crop = shot.crop((left, top, left + crop_w, top + crop_h))

    if crop.width > TARGET_WIDTH:
        scale = TARGET_WIDTH / crop.width
        crop = crop.resize((TARGET_WIDTH, int(crop.height * scale)), Image.NEAREST)
    else:
        scale = 1.0

    pixels = crop.load()
    cw, ch = crop.width, crop.height
    hud_top    = int(ch * HUD_TOP_SKIP)
    hud_bottom = int(ch * HUD_BOTTOM_SKIP)

    mask = bytearray(cw * ch)
    for y in range(hud_top, hud_bottom):
        row = y * cw
        for x in range(cw):
            r, g, b = pixels[x, y][:3]
            if pixel_matches(r, g, b):
                mask[row + x] = 1

    blobs = cluster_blobs(mask, cw, ch)
    if not blobs:
        return None

    crop_cx = cw / 2
    crop_cy = ch / 2
    def score(b):
        px, py = b["centroid"]
        dist = ((px - crop_cx) ** 2 + (py - crop_cy) ** 2) ** 0.5
        diag = (cw * cw + ch * ch) ** 0.5
        return b["pixels"] - (b["pixels"] * 0.5 * (dist / diag))
    blobs.sort(key=score, reverse=True)
    best = blobs[0]

    bx0, by0, bx1, by1 = best["bbox"]
    bbox_w = bx1 - bx0
    bbox_h = by1 - by0
    if bbox_w < MIN_BBOX or bbox_h < MIN_BBOX:
        return None

    aim_cx = (bx0 + bx1) / 2
    aim_cy = by0 + (bbox_h * HEAD_BIAS_FRAC)

    cx_screen = (aim_cx / scale) + left
    cy_screen = (aim_cy / scale) + top
    dx = int(cx_screen - cx)
    dy = int(cy_screen - cy)

    crop_area = cw * ch
    confidence = min(0.95, best["pixels"] / (crop_area * 0.02))
    return {
        "dx": dx, "dy": dy,
        "confidence": confidence,
        "pixels": best["pixels"],
        "blob_count": len(blobs),
    }


# ── Main loop ────────────────────────────────────────────
def engage():
    t0 = time.time()
    tgt = find_target()
    scan_ms = int((time.time() - t0) * 1000)

    if not tgt:
        log_event({'kind': 'scan', 'found': False, 'scan_ms': scan_ms})
        return 0
    if tgt["confidence"] < MIN_CONFIDENCE:
        log_event({
            'kind': 'scan', 'found': True, 'below_threshold': True,
            'confidence': round(tgt['confidence'], 3),
            'pixels': tgt['pixels'], 'blob_count': tgt['blob_count'],
            'scan_ms': scan_ms,
        })
        return 0

    # Jittered human-like snap
    jx = random.randint(-4, 4)
    jy = random.randint(-4, 4)
    snap_mouse(tgt["dx"] + jx, tgt["dy"] + jy)
    time.sleep((30 + random.randint(0, 40)) / 1000.0)

    # Burst size by confidence tier
    c = tgt["confidence"]
    if c < MIN_CONFIDENCE * 2:
        planned = 1
    elif c < MIN_CONFIDENCE * 4:
        planned = min(BURST_SIZE, 3)
    else:
        planned = BURST_SIZE + 1

    fired = 0
    trace = []
    for i in range(planned):
        fire_shot(SHOT_HOLD_MS + random.randint(-15, 15))
        fired += 1
        trace.append({'shot': i + 1, 'conf': round(c, 3)})
        if i >= planned - 1:
            break
        time.sleep(max(0.05, (SHOT_DELAY_MS + random.randint(-20, 20)) / 1000.0))
        # Rescan + micro-adjust if target moved
        nxt = find_target()
        if not nxt or nxt["confidence"] < MIN_CONFIDENCE * 0.6:
            trace.append({'shot': 'lost', 'conf': nxt['confidence'] if nxt else 0})
            break
        c = nxt["confidence"]
        if abs(nxt["dx"]) > 30 or abs(nxt["dy"]) > 30:
            snap_mouse(nxt["dx"] + random.randint(-3, 3),
                       nxt["dy"] + random.randint(-3, 3),
                       smoothing=3)

    log_event({
        'kind': 'engage',
        'fired': fired,
        'planned': planned,
        'initial_conf': round(tgt['confidence'], 3),
        'dx': tgt['dx'], 'dy': tgt['dy'],
        'pixels': tgt['pixels'],
        'blob_count': tgt['blob_count'],
        'scan_ms': scan_ms,
        'total_ms': int((time.time() - t0) * 1000),
        'trace': trace,
    })
    return fired


_paused = [False]

def toggle_pause():
    _paused[0] = not _paused[0]
    print("[ken_aimbot] paused" if _paused[0] else "[ken_aimbot] resumed")

def main():
    print("[ken_aimbot] started. stop: drop AIMBOT_STOP.flag on desktop or press F10 to pause.")
    print(f"[ken_aimbot] logging to {LOG_FILE.name}")
    maybe_trim_log()
    log_event({'kind': 'start', 'scan_interval_ms': SCAN_INTERVAL_MS,
               'min_confidence': MIN_CONFIDENCE, 'burst_size': BURST_SIZE,
               'head_bias': HEAD_BIAS_FRAC, 'center_frac': CENTER_FRAC})
    # Clear any stale stop flag from previous runs
    try:
        if STOP_FLAG.exists(): STOP_FLAG.unlink()
    except Exception:
        pass
    if HAS_KB:
        try: _kb.add_hotkey(PAUSE_HOTKEY, toggle_pause)
        except Exception: pass

    scans = 0
    fires = 0
    start = time.time()
    try:
        while True:
            if STOP_FLAG.exists():
                print("[ken_aimbot] stop flag detected, exiting")
                break
            if _paused[0]:
                time.sleep(0.25)
                continue
            try:
                fires += engage()
                scans += 1
            except Exception as e:
                log_event({'kind': 'error', 'msg': str(e)[:200]})
                time.sleep(0.1)
            time.sleep(SCAN_INTERVAL_MS / 1000.0)
            if scans % 50 == 0 and scans > 0:
                elapsed = time.time() - start
                print(f"[ken_aimbot] {scans} scans, {fires} shots, {elapsed:.0f}s uptime")
                log_event({'kind': 'heartbeat', 'scans': scans, 'shots': fires,
                           'uptime_s': round(elapsed, 1)})
    except KeyboardInterrupt:
        print("[ken_aimbot] interrupted")
    finally:
        if HAS_KB:
            try: _kb.unhook_all()
            except Exception: pass
        log_event({'kind': 'stop', 'scans': scans, 'shots': fires,
                   'uptime_s': round(time.time() - start, 1)})


if __name__ == "__main__":
    main()
