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
import random
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


def _pixel_matches(r, g, b, palette):
    """Return True if (r,g,b) matches any entry in the palette."""
    for _, rmin, rmax, gmin, gmax, bmin, bmax in palette:
        if rmin <= r <= rmax and gmin <= g <= gmax and bmin <= b <= bmax:
            return True
    return False


def _cluster_blobs(mask, w, h, min_size=18):
    """Iterative 4-connected flood fill over a boolean mask.
    Returns a list of blob dicts: {pixels, bbox, centroid}.
    Skips blobs smaller than min_size to drop HUD speckle."""
    visited = bytearray(w * h)
    blobs = []
    for start_y in range(h):
        row = start_y * w
        for start_x in range(w):
            idx = row + start_x
            if visited[idx] or not mask[idx]:
                continue
            # BFS this connected component
            stack = [(start_x, start_y)]
            visited[idx] = 1
            sum_x = 0
            sum_y = 0
            count = 0
            bx0, by0, bx1, by1 = start_x, start_y, start_x, start_y
            while stack:
                x, y = stack.pop()
                sum_x += x
                sum_y += y
                count += 1
                if x < bx0: bx0 = x
                if x > bx1: bx1 = x
                if y < by0: by0 = y
                if y > by1: by1 = y
                # 4-connected neighbors
                for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if not visited[nidx] and mask[nidx]:
                            visited[nidx] = 1
                            stack.append((nx, ny))
            if count >= min_size:
                blobs.append({
                    "pixels": count,
                    "bbox":   (bx0, by0, bx1, by1),
                    "centroid": (sum_x / count, sum_y / count),
                })
    return blobs


def find_target(palette_name="red", exclude_hud=True, head_bias=True):
    """Grab center screen crop, threshold for enemy pixels,
    cluster into discrete blobs via flood fill, pick the best
    target by size × proximity-to-crosshair, aim for the top
    of its bbox (head bias) instead of the centroid.

    Returns {found, dx, dy, confidence, bbox, blobs} where
    blobs is the count of distinct hot regions detected (for
    debugging + multi-enemy awareness)."""
    full = pyautogui.screenshot()
    w, h = full.size
    crop_w = int(w * CENTER_FRAC)
    crop_h = int(h * CENTER_FRAC)
    cx = w // 2
    cy = h // 2
    left = cx - crop_w // 2
    top  = cy - crop_h // 2
    crop = full.crop((left, top, left + crop_w, top + crop_h))

    # Downsample — 480w is plenty for centroid accuracy and
    # the flood-fill is O(n) in pixels so speed matters.
    target_w = 480
    if crop.width > target_w:
        scale = target_w / crop.width
        crop = crop.resize((target_w, int(crop.height * scale)), Image.NEAREST)
    else:
        scale = 1.0

    pixels = crop.load()
    palette = PALETTES.get(palette_name, PALETTES["red"])
    cw, ch = crop.width, crop.height

    # HUD exclusion zones — ignore top 10% (health bar) and
    # bottom 15% (weapon + ammo + grenade counter) of the crop.
    # These are the most common false-positive sources in Halo MCC.
    hud_top    = int(ch * 0.10) if exclude_hud else 0
    hud_bottom = int(ch * 0.85) if exclude_hud else ch

    # Build a boolean mask in a flat bytearray for fast flood fill.
    mask = bytearray(cw * ch)
    for y in range(hud_top, hud_bottom):
        row = y * cw
        for x in range(cw):
            r, g, b = pixels[x, y][:3]
            if _pixel_matches(r, g, b, palette):
                mask[row + x] = 1

    blobs = _cluster_blobs(mask, cw, ch, min_size=18)

    if not blobs:
        return {
            "found": False,
            "pixels": 0,
            "blobs": 0,
            "palette": palette_name,
            "screen": {"w": w, "h": h},
            "cropFrac": CENTER_FRAC,
        }

    # Rank candidates. Score = pixel count minus a small penalty
    # for distance from the crosshair (centered in the crop).
    # Bigger blobs win, but close-to-center ties go to the
    # closer one — this handles the common case where two
    # enemies are on screen and you want the one you were
    # already looking at.
    crop_cx = cw / 2
    crop_cy = ch / 2
    def score(blob):
        px, py = blob["centroid"]
        dist = ((px - crop_cx) ** 2 + (py - crop_cy) ** 2) ** 0.5
        # Normalize distance to crop diagonal so penalty is
        # bounded. ~50% of pixel count at max distance.
        diag = (cw * cw + ch * ch) ** 0.5
        return blob["pixels"] - (blob["pixels"] * 0.5 * (dist / diag))
    blobs.sort(key=score, reverse=True)
    best = blobs[0]

    bx0, by0, bx1, by1 = best["bbox"]
    bbox_w = bx1 - bx0
    bbox_h = by1 - by0

    # Head-bias aim point: top quarter of the bbox, horizontally
    # centered. Real blobs of enemy outline tend to follow the
    # silhouette — the head sits in the top ~25% of the bounding
    # rectangle. Falls back to centroid if head_bias off.
    if head_bias:
        aim_cx = (bx0 + bx1) / 2
        aim_cy = by0 + (bbox_h * 0.22)
    else:
        aim_cx, aim_cy = best["centroid"]

    # Rescale to full-screen pixel delta from crosshair.
    cx_screen = (aim_cx / scale) + left
    cy_screen = (aim_cy / scale) + top
    dx = int(cx_screen - cx)
    dy = int(cy_screen - cy)

    # Confidence: blob area normalized to crop area, saturate
    # at 2% match. Plus bbox minimum size check.
    crop_area = cw * ch
    if bbox_w < 8 or bbox_h < 8:
        return {
            "found": False,
            "pixels": best["pixels"],
            "blobs": len(blobs),
            "palette": palette_name,
            "screen": {"w": w, "h": h},
            "cropFrac": CENTER_FRAC,
            "reason": "bbox too small ({}x{})".format(bbox_w, bbox_h),
        }
    confidence = min(0.95, best["pixels"] / (crop_area * 0.02))

    return {
        "found": True,
        "pixels": best["pixels"],
        "blobs": len(blobs),
        "dx": dx,
        "dy": dy,
        "confidence": round(confidence, 3),
        "bbox": [bx0, by0, bx1, by1],
        "headBias": head_bias,
        "palette": palette_name,
        "screen": {"w": w, "h": h},
        "cropFrac": CENTER_FRAC,
    }


def snap_mouse(dx, dy, smoothing=5):
    """Move the mouse toward the target. Split into smoothing
    sub-steps so the motion registers as raw input rather than
    a single teleport (some games filter large single deltas).
    5 sub-steps with 8ms gaps = ~40ms total — visually smooth
    but still faster than a human can react, which is the
    point. Uses the ctypes mouse_event path — known to reach
    Halo MCC when the game is focused."""
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
        time.sleep(0.008)

def fire_shot(hold_ms=70):
    """Fire a single LMB press + release. 70ms hold is short
    enough to register as one click even on twitchy weapons
    (BR burst, sniper). Not so short it's filtered as noise."""
    import ctypes
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP   = 0x0004
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(hold_ms / 1000.0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def engage(palette_name, min_confidence, burst_size=3, shot_delay_ms=140,
           max_shots=5, rescan_between=True):
    """Full engagement loop: scan → snap → fire → rescan → fire
    → ... until target is lost OR max_shots reached OR
    rescan confidence drops below min_confidence.

    Returns a report with shots_fired, last_confidence, and a
    trace of each sub-shot so agent.js can log it to
    halo-events.jsonl.

    Confidence tiers inside the loop:
      - Below min_confidence         → bail out, no shots
      - min_confidence .. 2*min_conf → snap + 1 shot (single tap)
      - 2*min_conf .. 4*min_conf     → snap + burst of 3
      - Above 4*min_conf             → snap + full burst_size shots

    Between each shot we re-scan and micro-adjust the snap.
    The target can move; we track it shot-to-shot instead of
    committing to one fixed centroid. This is the "better
    control" Ken asked for — persistent target tracking
    instead of spray-and-pray on a stale centroid.
    """
    trace = []
    shots_fired = 0
    first = find_target(palette_name)
    if not first.get("found") or first.get("confidence", 0) < min_confidence:
        first["shots_fired"] = 0
        first["engaged"] = False
        return first

    confidence = first["confidence"]
    # Decide burst size based on confidence tier
    if confidence < min_confidence * 2:
        planned = 1
    elif confidence < min_confidence * 4:
        planned = min(burst_size, 3)
    else:
        planned = min(max_shots, burst_size + 1)

    # Human-like aim jitter: ±4 pixels so the snap isn't
    # pixel-perfect. A bot that always hits dead-center looks
    # synthetic + is detectable by anti-cheat heuristics.
    jitter_x = random.randint(-4, 4)
    jitter_y = random.randint(-4, 4)
    snap_mouse(first["dx"] + jitter_x, first["dy"] + jitter_y, smoothing=5)

    # Human reaction delay before the first shot — 45-95ms so
    # the first click feels reflexive, not mechanical.
    time.sleep((45 + random.randint(0, 50)) / 1000.0)

    for i in range(planned):
        # Jittered shot hold (55-90ms) mimics how a real
        # trigger press varies.
        fire_shot(hold_ms=55 + random.randint(0, 35))
        shots_fired += 1
        trace.append({"shot": i + 1, "confidence": confidence})
        if i >= planned - 1:
            break
        # Jittered cooldown between shots — ±30ms so bursts
        # sound like a human pressing fast, not a bot mashing.
        jittered_delay = shot_delay_ms + random.randint(-30, 30)
        time.sleep(max(80, jittered_delay) / 1000.0)
        if rescan_between:
            nxt = find_target(palette_name)
            if not nxt.get("found") or nxt.get("confidence", 0) < min_confidence * 0.6:
                # Target lost or faded — bail out mid-burst.
                trace.append({"shot": "lost", "confidence": nxt.get("confidence", 0)})
                break
            confidence = nxt["confidence"]
            # Micro-adjust if the target moved more than ~30px.
            # Add fresh jitter each adjustment so the tracking
            # looks like a real player making small corrections.
            if abs(nxt.get("dx", 0)) > 30 or abs(nxt.get("dy", 0)) > 30:
                jx = random.randint(-3, 3)
                jy = random.randint(-3, 3)
                snap_mouse(nxt["dx"] + jx, nxt["dy"] + jy, smoothing=3)
                time.sleep((8 + random.randint(0, 8)) / 1000.0)

    report = dict(first)
    report["shots_fired"] = shots_fired
    report["planned_shots"] = planned
    report["engaged"] = True
    report["trace"] = trace
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--palette", default="red", choices=list(PALETTES.keys()))
    parser.add_argument("--snap", action="store_true")
    parser.add_argument("--fire", action="store_true")
    parser.add_argument("--engage", action="store_true",
                        help="full engagement loop: scan→snap→burst→rescan→continue")
    parser.add_argument("--burst-size", type=int, default=3)
    parser.add_argument("--shot-delay", type=int, default=140)
    parser.add_argument("--max-shots", type=int, default=5)
    parser.add_argument("--min-confidence", type=float, default=0.05)
    args = parser.parse_args()

    t0 = time.time()

    if args.engage:
        target = engage(
            args.palette,
            args.min_confidence,
            burst_size=args.burst_size,
            shot_delay_ms=args.shot_delay,
            max_shots=args.max_shots,
        )
        target["scanMs"] = int((time.time() - t0) * 1000)
    else:
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
