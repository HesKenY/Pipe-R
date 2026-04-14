"""
Dedicated enemy detection via llama3.2-vision — tighter prompt,
faster cadence than halo_vision.py, used to feed a structured
"enemies on screen right now" signal into the driver and aimbot.

Where halo_vision.py asks a broad situational description (slow,
20s cadence), halo_enemy_detect.py asks ONE question: how many
enemies are in frame + what are they. Smaller prompt = faster
inference (~8-15s on llama3.2-vision).

Output:
    {
      "ok": true,
      "count": int,            # 0..N visible enemies
      "types": [str],          # e.g. ["elite", "grunt", "grunt"]
      "threat_level": "none" | "low" | "medium" | "high",
      "recommend": str,        # one action word
      "elapsedMs": int,
      "at": ISO
    }

Threat levels:
    none   — 0 enemies
    low    — 1 weak enemy (grunt/jackal alone)
    medium — 1 elite OR multiple grunts
    high   — 2+ elites, 1+ hunter, or brute + support

Intentionally keeps the prompt minimal so the model is fast.
No situation description, no narration, no prose.
"""

import sys
import json
import time
import re
import subprocess
import tempfile
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui required: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image

pyautogui.FAILSAFE = False

PROMPT = (
    "This is a Halo 2 first-person screen. Count the enemies VISIBLE "
    "right now (not friendly marines, not corpses, not UI elements). "
    "Respond with EXACTLY one line in this format:\n\n"
    "COUNT|TYPES|THREAT|RECOMMEND\n\n"
    "where:\n"
    "  COUNT     = integer 0-9 (visible enemies)\n"
    "  TYPES     = comma-separated enemy list (grunt, jackal, elite, "
    "hunter, brute, drone, flood, sentinel) or 'none'\n"
    "  THREAT    = none | low | medium | high\n"
    "  RECOMMEND = ONE action word: move_fwd, strafe_left, strafe_right, "
    "fire, ads, grenade, melee, reload, look_left, look_right, crouch, "
    "noop\n\n"
    "Respond with ONLY that one line. No prose, no explanation, no markdown."
)


def strip_ansi(s):
    s = re.sub(r"\x1b\[\??[0-9;]*[a-zA-Z]", "", s or "")
    s = re.sub(r"\x1b\][^\x07]*\x07", "", s)
    return s


def run_detect(model="llama3.2-vision"):
    t0 = time.time()
    shot = pyautogui.screenshot()
    w, h = shot.size
    target_w = 768  # smaller than halo_vision.py for speed
    if w > target_w:
        scale = target_w / w
        shot_small = shot.resize((target_w, int(h * scale)), Image.BILINEAR)
    else:
        shot_small = shot

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    shot_small.save(img_path, "PNG")

    try:
        input_blob = f"{img_path}\n{PROMPT}"
        result = subprocess.run(
            ["ollama", "run", model],
            input=input_blob,
            capture_output=True,
            text=True,
            timeout=35,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "error": f"ollama exit {result.returncode}",
                "stderr": (result.stderr or "")[:200],
                "at": datetime.now(timezone.utc).isoformat(),
                "elapsedMs": int((time.time() - t0) * 1000),
            }

        raw = strip_ansi(result.stdout or "").strip()
        line = ""
        for candidate in raw.splitlines():
            if "|" in candidate and len(candidate) > 5:
                line = candidate.strip()
                break
        if not line:
            line = raw.splitlines()[0] if raw else ""

        parts = [p.strip() for p in line.split("|")]
        # Parse COUNT
        try:
            count = int(re.search(r"\d+", parts[0] or "0").group(0))
        except Exception:
            count = 0

        types_raw = parts[1] if len(parts) > 1 else "none"
        types = [] if types_raw.lower() in ("none", "") else [
            t.strip().lower() for t in types_raw.split(",") if t.strip()
        ]
        threat    = parts[2].lower() if len(parts) > 2 else "none"
        if threat not in ("none", "low", "medium", "high"):
            threat = "low" if count > 0 else "none"
        recommend = parts[3].lower() if len(parts) > 3 else "noop"

        return {
            "ok": True,
            "count": count,
            "types": types,
            "threat_level": threat,
            "recommend": recommend,
            "raw": line[:200],
            "model": model,
            "at": datetime.now(timezone.utc).isoformat(),
            "elapsedMs": int((time.time() - t0) * 1000),
        }
    finally:
        try:
            import os
            os.unlink(img_path)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.2-vision")
    args = parser.parse_args()
    result = run_detect(model=args.model)
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
