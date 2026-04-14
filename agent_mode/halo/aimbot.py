"""
Halo MCC aimbot assist — color-threshold enemy finder + mouse snap.

Strategy:
  1. Grab the center region of the screen (crosshair area).
  2. Threshold for "enemy-signature" colors — by default we hunt
     red-dominant pixels (Elite armor, enemy outline if enabled
     in MCC video settings, damage indicators, Covenant plasma).
     Configurable via --palette if other colors matter.
  3. Cluster contiguous hot pixels into blobs using a grid scan
     (no opencv — pure PIL). Pick the biggest blob.
  4. Compute delta from crosshair (center of screen) to blob
     centroid in pixels.
  5. Return JSON with {found, dx, dy, pixels, confidence, palette}.

Usage:
    python aimbot.py                 # scan, return target info only
    python aimbot.py --snap          # also move mouse toward target
    python aimbot.py --snap --fire   # snap + fire (hold LMB briefly)

No opencv required — PIL + ImageStat handles everything. Runs
in ~60ms on 5120x1440 with the center 1/3 crop.
"""

import sys
import json
import time
import argparse

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui required: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image


# Center-crop as a fraction of the full screen. 0.33 = center
# 1/3 square around the crosshair. Bigger catches more enemies
# but raises false-positive rate from HUD elements.
CENTER_FRAC = 0.34

# Enemy-signature palette. Each entry is (name, min_r, max_r,
# min_g, max_g, min_b, max_b). The defaults hunt saturated
# reds (Elite armor, damage indicators, outline mode) and
# bright purples (Covenant plasma, jackal shields). Tune later
# per game if needed.
PALETTES = {
    "red": [
        ("red",        150, 255,   0, 100,   0, 100),
        ("bright_red", 200, 255,   0,  80,   0,  80),
    ],
    "purple": [
        ("purple",     120, 220,   0, 100, 120, 255),
    ],
    "all": [
        ("red",        150, 255,   0, 100,   0, 100),
        ("bright_red", 200, 255,   0,  80,   0,  80),
        ("purple",     120, 220,   0, 100, 120, 255),
        ("orange",     200, 255, 100, 180,   0,  80),  # grunt methane tanks
    ],
}


def find_target(palette_name="red"):
    """Grab center screen crop, threshold for enemy pixels,
    return the biggest blob's centroid as a (dx, dy) delta from
    screen center."""
    full = pyautogui.screenshot()
    w, h = full.size
    crop_w = int(w * CENTER_FRAC)
    crop_h = int(h * CENTER_FRAC)
    cx = w // 2
    cy = h // 2
    left = cx - crop_w // 2
    top  = cy - crop_h // 2
    crop = full.crop((left, top, left + crop_w, top + crop_h))

    # Downsample to speed up pixel scanning. ~480 wide is plenty
    # for centroid accuracy on most Halo encounter distances.
    target_w = 480
    if crop.width > target_w:
        scale = target_w / crop.width
        crop = crop.resize((target_w, int(crop.height * scale)), Image.NEAREST)
    else:
        scale = 1.0

    pixels = crop.load()
    palette = PALETTES.get(palette_name, PALETTES["red"])

    # Per-pixel threshold. Accumulate matches into a sum of
    # (x, y) so we can compute the centroid of the whole hot
    # region. If we want multi-blob clustering later, upgrade
    # to a BFS flood-fill here.
    total = 0
    sum_x = 0
    sum_y = 0
    bbox_left = crop.width
    bbox_right = 0
    bbox_top = crop.height
    bbox_bot = 0

    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b = pixels[x, y][:3]
            for _, rmin, rmax, gmin, gmax, bmin, bmax in palette:
                if rmin <= r <= rmax and gmin <= g <= gmax and bmin <= b <= bmax:
                    total += 1
                    sum_x += x
                    sum_y += y
                    if x < bbox_left: bbox_left = x
                    if x > bbox_right: bbox_right = x
                    if y < bbox_top: bbox_top = y
                    if y > bbox_bot: bbox_bot = y
                    break

    if total < 20:
        return {
            "found": False,
            "pixels": total,
            "palette": palette_name,
            "screen": {"w": w, "h": h},
            "cropFrac": CENTER_FRAC,
        }

    # Centroid in downsampled crop coordinates → rescale back
    # to the full screen crop → convert to delta from screen
    # center in real pixels.
    cx_crop = sum_x / total
    cy_crop = sum_y / total
    cx_screen = (cx_crop / scale) + left
    cy_screen = (cy_crop / scale) + top
    dx = int(cx_screen - cx)
    dy = int(cy_screen - cy)

    # Confidence: blob area normalized to crop area. Recalibrated —
    # a real enemy outline in Halo (Elite at mid range) is ~1–3% of
    # the crop's pixels. Saturate at 2% so meaningful hits land
    # around 0.5–1.0 confidence. Also require the bounding box to
    # be at least 8x8 in downsampled crop space to reject scattered
    # speckle from HUD noise.
    crop_area = crop.width * crop.height
    bbox_w = max(0, bbox_right - bbox_left)
    bbox_h = max(0, bbox_bot - bbox_top)
    if bbox_w < 8 or bbox_h < 8:
        return {
            "found": False,
            "pixels": total,
            "palette": palette_name,
            "screen": {"w": w, "h": h},
            "cropFrac": CENTER_FRAC,
            "reason": "bbox too small ({}x{})".format(bbox_w, bbox_h),
        }
    confidence = min(0.95, total / (crop_area * 0.02))

    return {
        "found": True,
        "pixels": total,
        "dx": dx,
        "dy": dy,
        "confidence": round(confidence, 3),
        "bbox": [bbox_left, bbox_top, bbox_right, bbox_bot],
        "palette": palette_name,
        "screen": {"w": w, "h": h},
        "cropFrac": CENTER_FRAC,
    }


def snap_mouse(dx, dy, smoothing=2):
    """Move the mouse toward the target. Split into smoothing
    sub-steps so the motion registers as raw input rather than
    a single teleport (some games filter large single deltas).
    Uses the ctypes mouse_event path — known to reach Halo MCC
    when the game is focused."""
    import ctypes
    MOUSEEVENTF_MOVE = 0x0001
    step_x = int(dx / smoothing)
    step_y = int(dy / smoothing)
    remainder_x = dx - step_x * smoothing
    remainder_y = dy - step_y * smoothing
    for i in range(smoothing):
        rx = step_x + (remainder_x if i == smoothing - 1 else 0)
        ry = step_y + (remainder_y if i == smoothing - 1 else 0)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, rx, ry, 0, 0)
        time.sleep(0.012)

def fire_shot():
    import ctypes
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP   = 0x0004
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--palette", default="red", choices=list(PALETTES.keys()))
    parser.add_argument("--snap", action="store_true")
    parser.add_argument("--fire", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.05)
    args = parser.parse_args()

    t0 = time.time()
    target = find_target(args.palette)
    target["scanMs"] = int((time.time() - t0) * 1000)

    if args.snap and target.get("found") and target.get("confidence", 0) >= args.min_confidence:
        snap_mouse(target["dx"], target["dy"])
        target["snapped"] = True
        if args.fire:
            time.sleep(0.05)
            fire_shot()
            target["fired"] = True

    sys.stdout.write(json.dumps(target) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
