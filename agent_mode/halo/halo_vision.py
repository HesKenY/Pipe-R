"""
Halo MCC visual describer — uses llama3.2-vision to actually
SEE the screen instead of relying on OCR of HUD fragments.

Runs slowly (8-20s per invocation on a 14B vision model) so it
is NOT called per-tick. Instead a separate auto-vision loop in
agent.js fires this every ~15-20 seconds and caches the result.
Every drive/observe prompt then includes the most recent cached
description alongside the OCR + motion signals.

Usage:
    python halo_vision.py                       # one-shot, print to stdout
    python halo_vision.py --model llama3.2-vision

Outputs JSON:
    {
      "ok": true,
      "description": "<1-3 line description>",
      "enemies_visible": bool (best-guess),
      "situation": "combat|exploration|menu|transition|unknown",
      "weapon_hint": "<short>",
      "elapsedMs": int,
      "at": ISO
    }
"""

import sys
import json
import time
import tempfile
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import pyautogui
except Exception as e:
    sys.stderr.write("pyautogui import failed: " + str(e) + "\n")
    sys.exit(2)

from PIL import Image

pyautogui.FAILSAFE = False

PROMPT = (
    "This is a screenshot from Halo 2 / Halo MCC (first-person shooter, "
    "Master Chief perspective). Describe in ONE short line what is on "
    "screen. Answer these four fields on ONE line separated by pipes:\n\n"
    "SITUATION|ENEMIES|WEAPON|SUGGESTION\n\n"
    "where SITUATION is one of: combat, exploration, menu, transition, "
    "cutscene, death, unknown.\n"
    "ENEMIES is a short list of what enemies are visible (e.g. 'elite, "
    "2 grunts' or 'none') or 'none' if the screen is empty.\n"
    "WEAPON is the weapon the player is holding based on the HUD model "
    "(e.g. 'battle rifle', 'plasma pistol', 'unknown').\n"
    "SUGGESTION is one action word from: move_fwd, strafe_left, "
    "strafe_right, look_left, look_right, fire, ads, reload, grenade, "
    "melee, crouch, noop.\n\n"
    "Respond with exactly ONE line in the SITUATION|ENEMIES|WEAPON|SUGGESTION "
    "format. No prose, no explanations, no markdown."
)


def run_vision(model="llama3.2-vision"):
    t0 = time.time()
    # Capture screen + downsample for speed. Vision models don't
    # need 5K — 896 wide is enough for scene understanding and
    # keeps inference under 20s on a 7.8GB model.
    shot = pyautogui.screenshot()
    w, h = shot.size
    target_w = 896
    if w > target_w:
        scale = target_w / w
        shot_small = shot.resize((target_w, int(h * scale)), Image.BILINEAR)
    else:
        shot_small = shot

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    shot_small.save(img_path, "PNG")

    try:
        # Ollama vision CLI takes the image path in the prompt body
        # via a special prefix. On recent ollama versions the
        # supported syntax is `/path/to/img.png<newline>prompt`.
        input_blob = f"{img_path}\n{PROMPT}"
        result = subprocess.run(
            ["ollama", "run", model],
            input=input_blob,
            capture_output=True,
            text=True,
            timeout=45,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "error": f"ollama exit {result.returncode}",
                "stderr": (result.stderr or "")[:300],
                "at": datetime.now(timezone.utc).isoformat(),
                "elapsedMs": int((time.time() - t0) * 1000),
            }

        raw = (result.stdout or "").strip()
        # Strip ANSI noise
        import re
        raw = re.sub(r"\x1b\[\??[0-9;]*[a-zA-Z]", "", raw)
        raw = re.sub(r"\x1b\][^\x07]*\x07", "", raw)

        # Find the first line that contains a pipe separator
        line = ""
        for candidate in raw.splitlines():
            if "|" in candidate and len(candidate) > 10:
                line = candidate.strip()
                break
        if not line:
            line = raw.splitlines()[0] if raw else ""

        parts = [p.strip() for p in line.split("|")]
        situation     = parts[0] if len(parts) > 0 else "unknown"
        enemies       = parts[1] if len(parts) > 1 else "none"
        weapon        = parts[2] if len(parts) > 2 else "unknown"
        suggestion    = parts[3] if len(parts) > 3 else "noop"

        return {
            "ok": True,
            "description": line[:240],
            "raw": raw[:500],
            "situation": situation.lower(),
            "enemies": enemies,
            "enemies_visible": enemies.lower() != "none" and enemies != "",
            "weapon_hint": weapon,
            "suggestion": suggestion.lower(),
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
    result = run_vision(model=args.model)
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
