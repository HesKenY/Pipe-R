"""
Pokemon Crystal visual describer — uses llama3.2-vision to SEE the
game screen. Much more reliable than OCR for pixel-art GBC games.

Runs every ~15s in a background loop. Caches result for the drive
prompt. Detects: battle screen, overworld, menu, dialogue, title,
pokemon center, shop, etc.

Output JSON:
    {
      "ok": true,
      "description": "short scene description",
      "situation": "battle|overworld|menu|dialogue|title|pokecenter|shop|unknown",
      "pokemon_visible": "player's pokemon, opponent's pokemon if in battle",
      "hp_status": "low/mid/full or unknown",
      "suggestion": "next action",
      "at": ISO,
      "elapsedMs": int
    }
"""

import os, sys, json, time, subprocess, tempfile, re
from datetime import datetime, timezone

try:
    import pyautogui
except:
    sys.exit(2)
from PIL import Image
import ctypes
from ctypes import wintypes

pyautogui.FAILSAFE = False

PROMPT = (
    "This is a screenshot from Pokemon Crystal (Game Boy Color game "
    "running in an emulator). Describe what you see in ONE line using "
    "this pipe-separated format:\n\n"
    "SITUATION|POKEMON|HP|ACTION\n\n"
    "SITUATION: one of battle, overworld, menu, dialogue, title, "
    "pokecenter, shop, evolution, intro, unknown\n"
    "POKEMON: what pokemon are visible (e.g. 'totodile vs pidgey' "
    "or 'player walking' or 'starter selection' or 'none')\n"
    "HP: health status if in battle (e.g. 'player:full foe:low' "
    "or 'unknown' if not in battle)\n"
    "ACTION: best next GBC button from: a, b, start, up, down, "
    "left, right, noop\n\n"
    "ONE line only. No prose."
)


def find_mgba():
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, None)
        while hwnd:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if "mGBA" in title or "Crystal" in title or "Pokemon" in title:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        if rect.right - rect.left > 100:
                            return (rect.left, rect.top, rect.right, rect.bottom)
            hwnd = user32.GetWindow(hwnd, 2)
    except:
        pass
    return None


def run_vision(model="llama3.2-vision"):
    t0 = time.time()

    rect = find_mgba()
    if rect:
        l, t, r, b = rect
        shot = pyautogui.screenshot(region=(l, t, r-l, b-t))
    else:
        shot = pyautogui.screenshot()

    # Upscale GBC screen for better vision model recognition
    # mGBA window is small (~336x348), vision models work better at 512+
    w, h = shot.size
    if w < 512:
        scale = 512 / w
        shot = shot.resize((512, int(h * scale)), Image.NEAREST)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    shot.save(img_path, "PNG")

    try:
        input_blob = f"{img_path}\n{PROMPT}"
        flags = 0x08000000 if os.name == "nt" else 0
        result = subprocess.run(
            ["ollama", "run", model],
            input=input_blob,
            capture_output=True, text=True,
            timeout=45, encoding="utf-8", errors="replace",
            creationflags=flags,
        )
        elapsed = int((time.time() - t0) * 1000)

        if result.returncode != 0:
            return {"ok": False, "error": f"exit {result.returncode}", "at": datetime.now(timezone.utc).isoformat(), "elapsedMs": elapsed}

        raw = re.sub(r"\x1b\[\??[0-9;]*[a-zA-Z]", "", (result.stdout or "").strip())
        raw = re.sub(r"\x1b\][^\x07]*\x07", "", raw)

        # Parse pipe-separated response
        line = ""
        for candidate in raw.split("\n"):
            if "|" in candidate:
                line = candidate.strip()
                break
        if not line:
            line = raw.split("\n")[0] if raw else ""

        parts = [p.strip() for p in line.split("|")]
        situation = parts[0].lower() if len(parts) > 0 else "unknown"
        pokemon = parts[1] if len(parts) > 1 else ""
        hp = parts[2] if len(parts) > 2 else "unknown"
        action = parts[3].lower() if len(parts) > 3 else "noop"

        valid_situations = {"battle","overworld","menu","dialogue","title","pokecenter","shop","evolution","intro","unknown"}
        if situation not in valid_situations:
            situation = "unknown"

        return {
            "ok": True,
            "description": line,
            "situation": situation,
            "pokemon_visible": pokemon,
            "hp_status": hp,
            "suggestion": action,
            "at": datetime.now(timezone.utc).isoformat(),
            "elapsedMs": elapsed,
        }
    finally:
        try:
            os.unlink(img_path)
        except:
            pass


if __name__ == "__main__":
    model = "llama3.2-vision"
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
    r = run_vision(model)
    print(json.dumps(r, indent=2))
