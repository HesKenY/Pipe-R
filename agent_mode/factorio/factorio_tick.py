"""
Factorio tick — screen capture + HUD OCR + activity detection.

Same architecture as halo_tick.py. Captures the Factorio window,
OCRs key HUD regions, detects activity level.

Output JSON:
    {
      "at": ISO,
      "w": int, "h": int,
      "resources": str,    # top-left resource counts
      "alerts": str,       # alert icons/text
      "minimap": str,      # minimap region OCR
      "center": str,       # center screen text (research, alerts)
      "toolbar": str,      # bottom toolbar/hotbar
      "motion": float,     # 0..1 pixel-delta vs last frame
      "bright": float,     # mean brightness 0..1
      "activity": str,     # building | researching | defending | exploring | idle | menu
      "foundWindow": bool
    }
"""

import json
import sys
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui import failed: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image, ImageChops
import ctypes
from ctypes import wintypes

pyautogui.FAILSAFE = False

PREV_FRAME_PATH = Path(tempfile.gettempdir()) / "_factorio_prev_frame.png"


def find_factorio_window():
    """Find the Factorio window and return (left, top, right, bottom) or None."""
    try:
        user32 = ctypes.windll.user32
        TITLES = ["Factorio"]
        hwnd = user32.FindWindowW(None, None)
        while hwnd:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    for t in TITLES:
                        if t in title:
                            rect = wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            if rect.right - rect.left > 200 and rect.bottom - rect.top > 200:
                                return (rect.left, rect.top, rect.right, rect.bottom)
                            break
            hwnd = user32.GetWindow(hwnd, 2)
        return None
    except Exception as e:
        sys.stderr.write("factorio window search failed: " + str(e) + "\n")
        return None


def compute_motion(current):
    """Compare current frame vs saved previous frame. Returns 0..1."""
    if not PREV_FRAME_PATH.exists():
        current.save(str(PREV_FRAME_PATH))
        return 0.0
    try:
        prev = Image.open(str(PREV_FRAME_PATH))
        small_cur = current.resize((128, 72))
        small_prev = prev.resize((128, 72))
        diff = ImageChops.difference(small_cur.convert("L"), small_prev.convert("L"))
        pixels = list(diff.getdata())
        motion = sum(pixels) / (len(pixels) * 255.0)
        current.save(str(PREV_FRAME_PATH))
        return round(motion, 4)
    except Exception:
        current.save(str(PREV_FRAME_PATH))
        return 0.0


def mean_brightness(img):
    small = img.resize((64, 36)).convert("L")
    pixels = list(small.getdata())
    return round(sum(pixels) / (len(pixels) * 255.0), 3)


def classify_activity(motion, bright, ocr_texts):
    """Coarse activity label from motion + brightness + OCR hints."""
    all_text = " ".join(ocr_texts).lower()
    if "under attack" in all_text or "destroyed" in all_text:
        return "defending"
    if bright < 0.05:
        return "menu"
    if "research" in all_text:
        return "researching"
    if motion > 0.08:
        return "building"
    if motion > 0.02:
        return "exploring"
    return "idle"


def ocr_region(img, box, label=""):
    """OCR a cropped region. Returns best-effort text."""
    try:
        import pytesseract
        crop = img.crop(box)
        text = pytesseract.image_to_string(crop, config="--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .:/-+%").strip()
        return text[:120]
    except Exception:
        return ""


def main():
    rect = find_factorio_window()
    if rect:
        left, top, right, bottom = rect
        shot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
        found = True
    else:
        shot = pyautogui.screenshot()
        found = False

    w, h = shot.size
    motion = compute_motion(shot)
    bright = mean_brightness(shot)

    # HUD regions (Factorio default layout)
    # Resources — top left
    resources = ocr_region(shot, (0, 0, int(w * 0.25), int(h * 0.05)), "resources")
    # Alerts — top right
    alerts = ocr_region(shot, (int(w * 0.75), 0, w, int(h * 0.08)), "alerts")
    # Minimap — top right corner
    minimap = ocr_region(shot, (int(w * 0.82), int(h * 0.02), w, int(h * 0.25)), "minimap")
    # Center — research complete, alerts, tooltips
    center = ocr_region(shot, (int(w * 0.3), int(h * 0.4), int(w * 0.7), int(h * 0.6)), "center")
    # Toolbar — bottom
    toolbar = ocr_region(shot, (int(w * 0.2), int(h * 0.92), int(w * 0.8), h), "toolbar")

    activity = classify_activity(motion, bright, [resources, alerts, center])

    result = {
        "at": datetime.now(timezone.utc).isoformat(),
        "w": w, "h": h,
        "resources": resources,
        "alerts": alerts,
        "minimap": minimap,
        "center": center,
        "toolbar": toolbar,
        "motion": motion,
        "bright": bright,
        "activity": activity,
        "foundWindow": found,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
