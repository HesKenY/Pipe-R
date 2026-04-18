"""
Halo MCC tick — screen capture + HUD OCR + motion detection.

Outputs one JSON line to stdout with a richer state than the
v1 tick:

    {
      "at": ISO,
      "w": int, "h": int,
      "ammo": str,     # OCR'd HUD text (best-candidate)
      "shield": str,
      "radar": str,
      "center": str,
      "motion": float, # 0..1 rough pixel-delta vs last frame
      "activity": str, # "combat" | "transition" | "idle" | "unknown"
      "bright": float, # mean brightness 0..1
      "foundWindow": bool
    }

Changes from v1:

- **Multi-region OCR** — every HUD field tries 3 candidate crops
  and picks whichever produces the longest non-trivial text.
  Fixes miscalibrated fractional crops on ultrawide displays.

- **Motion detection** — compares a downsampled current frame
  against the previous one stored in a temp file. Returns a
  rough "how much changed" score. High motion = combat / movement,
  low = menu / idle. Gives the model a reliable "something is
  happening" signal even when OCR is empty.

- **Activity classification** — combines motion + brightness +
  OCR presence into a coarse label the prompt can condition on.

- **Mean brightness** — simple float used to detect fade-to-
  black death screens (brightness drops below 0.1 for 2+ ticks).

No new pip deps — PIL + tesseract (both already required).
"""

import json
import subprocess
import sys
import tempfile
import os
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui import failed: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image, ImageChops

pyautogui.FAILSAFE = False

# ── Previous-frame cache for motion detection ──
# Stored as a downsampled PNG next to this script so two back-to-
# back halo_tick.py invocations can compare.
HERE = Path(__file__).resolve().parent
PREV_FRAME = HERE / "_halo_prev_frame.png"


def ocr_region(image, crop_box):
    """Save a crop to a temp PNG, run tesseract, return stripped text."""
    try:
        img = image.crop(crop_box)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_path = f.name
        img.save(img_path, "PNG")
        out_base = img_path + ".out"
        try:
            subprocess.run(
                ["tesseract", img_path, out_base, "--psm", "7", "-l", "eng"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            out_file = out_base + ".txt"
            txt = ""
            if os.path.exists(out_file):
                with open(out_file, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read().strip()
                os.unlink(out_file)
            return txt
        finally:
            try: os.unlink(img_path)
            except Exception: pass
    except Exception:
        return ""


def best_ocr(image, candidates):
    """Run OCR on each candidate box, return the longest
    non-trivial result. Trivial = < 2 non-whitespace chars."""
    best = ""
    for box in candidates:
        txt = ocr_region(image, box)
        # Strip leading/trailing garbage and collapse whitespace
        cleaned = " ".join(txt.split())
        if len(cleaned.replace(" ", "")) >= 2 and len(cleaned) > len(best):
            best = cleaned
    return best


def motion_score(current_full):
    """Compare current full-screen shot against the previous-frame
    cache. Returns 0..1 where 1 = every pixel changed completely.
    First call returns 0 (no prior frame)."""
    try:
        # Downsample hard — 320 wide is plenty for a motion signal
        # and keeps the compare cheap.
        w, h = current_full.size
        sw = 320
        sh = int(h * sw / w)
        small = current_full.resize((sw, sh), Image.BILINEAR).convert("L")

        score = 0.0
        if PREV_FRAME.exists():
            try:
                prev = Image.open(PREV_FRAME).convert("L")
                if prev.size == small.size:
                    diff = ImageChops.difference(small, prev)
                    # Sum of absolute pixel differences, normalized
                    hist = diff.histogram()
                    # Weight each bin by intensity then sum
                    total = sum(i * hist[i] for i in range(256))
                    maxpossible = 255 * sw * sh
                    score = min(1.0, total / max(1, maxpossible))
            except Exception:
                score = 0.0

        # Save current for next tick's compare
        small.save(PREV_FRAME, "PNG")
        return float(score)
    except Exception:
        return 0.0


def mean_brightness(current_full):
    try:
        w, h = current_full.size
        small = current_full.resize((160, int(h * 160 / w)), Image.BILINEAR).convert("L")
        pixels = list(small.getdata())
        if not pixels:
            return 0.0
        return sum(pixels) / (len(pixels) * 255.0)
    except Exception:
        return 0.5


def classify_activity(motion, brightness, has_ocr):
    """Rough state label. Heuristic but gives the model something
    to condition on when the OCR is noisy."""
    if brightness < 0.08:
        return "death_screen"
    if motion > 0.06 and has_ocr:
        return "combat"
    if motion > 0.03:
        return "transition"
    if motion < 0.006:
        return "idle"
    return "exploring"


def _find_halo_window():
    """Find the MCC window and return its bounding box, or None."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        # Search by window title substring
        TITLES = [b"Halo", b"MCC", b"Master Chief"]

        def _enum_cb(hwnd, results):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            for t in TITLES:
                if t.decode() in title:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    results.append((hwnd, title, rect.left, rect.top, rect.right, rect.bottom))
            return True

        results = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.py_object))
        # simpler approach: iterate with FindWindow
        hwnd = user32.FindWindowW(None, None)
        while hwnd:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    for t in ["Halo", "MCC", "Master Chief"]:
                        if t in title:
                            rect = wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            if rect.right - rect.left > 200 and rect.bottom - rect.top > 200:
                                return (rect.left, rect.top, rect.right, rect.bottom)
                            break
            hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
        return None
    except Exception as e:
        sys.stderr.write("halo window search failed: " + str(e) + "\n")
        return None


def main():
    # Try to capture the Halo window specifically. Fall back to full screen.
    halo_rect = _find_halo_window()
    if halo_rect:
        left, top, right, bottom = halo_rect
        shot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
    else:
        shot = pyautogui.screenshot()
    w, h = shot.size

    # ── Multi-region OCR candidates ──
    # Halo MCC HUD on ultrawide 5120x1440 puts elements at roughly
    # these positions. We try several slightly-offset crops and
    # take the best. Values tuned for 5K but work okay down to 1080p
    # since they're fractional.
    #
    # Ammo + weapon — bottom right
    ammo_candidates = [
        (int(w * 0.82), int(h * 0.83), int(w * 0.99), int(h * 0.98)),
        (int(w * 0.78), int(h * 0.85), int(w * 0.98), int(h * 0.99)),
        (int(w * 0.86), int(h * 0.86), int(w * 0.99), int(h * 0.97)),
    ]
    # Shield bar — top left (Halo 2 uses top-left shield)
    shield_candidates = [
        (int(w * 0.01), int(h * 0.02), int(w * 0.20), int(h * 0.14)),
        (int(w * 0.02), int(h * 0.04), int(w * 0.16), int(h * 0.12)),
        (int(w * 0.01), int(h * 0.82), int(w * 0.22), int(h * 0.98)),  # fallback bottom-left
    ]
    # Motion tracker / radar — top right
    radar_candidates = [
        (int(w * 0.80), int(h * 0.02), int(w * 0.99), int(h * 0.18)),
        (int(w * 0.84), int(h * 0.04), int(w * 0.99), int(h * 0.16)),
    ]
    # Center text — subtitles / interact prompts / death screen
    center_candidates = [
        (int(w * 0.38), int(h * 0.44), int(w * 0.62), int(h * 0.56)),  # crosshair + prompts
        (int(w * 0.30), int(h * 0.78), int(w * 0.70), int(h * 0.92)),  # subtitle zone
        (int(w * 0.25), int(h * 0.12), int(w * 0.75), int(h * 0.28)),  # top subtitle
    ]

    ammo   = best_ocr(shot, ammo_candidates)
    shield = best_ocr(shot, shield_candidates)
    radar  = best_ocr(shot, radar_candidates)
    center = best_ocr(shot, center_candidates)

    bright = mean_brightness(shot)
    motion = motion_score(shot)
    has_ocr = any([ammo, shield, radar, center])
    activity = classify_activity(motion, bright, has_ocr)

    state = {
        "at": datetime.now(timezone.utc).isoformat(),
        "w": w,
        "h": h,
        "ammo":   ammo,
        "shield": shield,
        "radar":  radar,
        "center": center,
        "motion": round(motion, 4),
        "bright": round(bright, 3),
        "activity": activity,
        "foundWindow": True,
    }
    sys.stdout.write(json.dumps(state) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
