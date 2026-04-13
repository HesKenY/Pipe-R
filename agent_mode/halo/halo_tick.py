"""
Halo MCC tick — single-shot screen capture + HUD OCR.

Outputs one JSON line to stdout:
    {"at": "...", "w": int, "h": int, "ammo": str, "shield": str,
     "radar": str, "center": str, "foundWindow": bool}

Requires pyautogui + Tesseract in PATH. No other pip deps.
Designed for the Ken AI learning loop so one Python invocation per
Node tick can grab a state snapshot of whatever is currently on
screen. Crops are rough fractional regions — Halo MCC layouts shift
across H1/H2/H3/Reach/4 so we don't try to be pixel-perfect.
"""

import json
import subprocess
import sys
import tempfile
import os
from datetime import datetime, timezone

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui import failed: " + str(e) + "\n")
    sys.exit(2)

# Don't raise for failsafe (top-left corner panic abort) — Ken may
# move the mouse there while we're running.
pyautogui.FAILSAFE = False


def ocr(image, crop_box=None):
    """Save a cropped PIL image to a temp PNG, run tesseract on it,
    return the stripped text. Empty string on any failure."""
    try:
        img = image if crop_box is None else image.crop(crop_box)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_path = f.name
        img.save(img_path, "PNG")
        out_base = img_path + ".out"
        try:
            # --psm 7 = single text line, -c tessedit_char_whitelist keeps
            # HUD digits + slashes + letters. Fast mode.
            proc = subprocess.run(
                ["tesseract", img_path, out_base, "--psm", "7", "-l", "eng"],
                capture_output=True, text=True, timeout=6
            )
            txt = ""
            out_file = out_base + ".txt"
            if os.path.exists(out_file):
                with open(out_file, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read().strip()
                os.unlink(out_file)
            return txt
        finally:
            try: os.unlink(img_path)
            except Exception: pass
    except Exception as e:
        return ""


def main():
    shot = pyautogui.screenshot()
    w, h = shot.size

    # Fractional HUD crop regions tuned for 1080p+ landscape. Halo
    # MCC puts ammo bottom-right, shield bar top-left, radar top-
    # right. These boxes are intentionally generous.
    ammo_box   = (int(w * 0.78), int(h * 0.82), int(w * 0.99), int(h * 0.99))
    shield_box = (int(w * 0.01), int(h * 0.82), int(w * 0.22), int(h * 0.99))
    radar_box  = (int(w * 0.78), int(h * 0.01), int(w * 0.99), int(h * 0.22))
    center_box = (int(w * 0.35), int(h * 0.35), int(w * 0.65), int(h * 0.65))

    state = {
        "at": datetime.now(timezone.utc).isoformat(),
        "w": w,
        "h": h,
        "ammo":   ocr(shot, ammo_box),
        "shield": ocr(shot, shield_box),
        "radar":  ocr(shot, radar_box),
        "center": ocr(shot, center_box),
        "foundWindow": True,
    }
    sys.stdout.write(json.dumps(state) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
