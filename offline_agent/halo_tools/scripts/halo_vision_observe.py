"""
halo_vision_observe.py — KenAI-native vision observer loop

Takes a screenshot every N seconds (default 20), asks
`llama3.2-vision` to describe what's on screen, extracts
structured signals, and appends JSONL rows to:

    brain/corpus/halo_tools_logs/halo-vision.jsonl

NO memory access. NO writes to the game. Purely observation
for the learning corpus. Fires only while Halo has foreground
focus — no point reading a vision model on Ken's desktop.

Also watches for the phrase "mission complete" in the vision
description and calls the KenAI API to auto-flip the mission
tracker. Ken can also mark complete by hand from the UI.

Stop:
  - drop VISION_STOP.flag next to the script
  - OR taskkill the python process

Usage:
    python halo_vision_observe.py              # default 20s cadence
    python halo_vision_observe.py --interval 30
    python halo_vision_observe.py --one-shot   # single read + exit
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    print("pyautogui required: pip install pyautogui Pillow")
    sys.exit(2)

from PIL import Image

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "brain" / "corpus" / "halo_tools_logs" / "halo-vision.jsonl"
STOP_FLAG = HERE / "VISION_STOP.flag"

KENAI_BASE = os.environ.get("KENAI_URL", "http://127.0.0.1:7778")
OLLAMA_BASE = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
VISION_MODEL = os.environ.get("VISION_MODEL", "llama3.2-vision")
# keep_alive tells Ollama to keep the vision model loaded in
# VRAM between calls instead of cold-loading each time.
KEEP_ALIVE = "10m"

PROMPT = (
    "This is a screenshot of Halo 2 MCC. Respond with ONE short line in "
    "this exact pipe-delimited format, nothing else:\n"
    "  situation|enemies|weapon|suggested_action\n\n"
    "situation: combat | exploration | menu | cutscene | death_screen | mission_complete | transition\n"
    "enemies: none | OR comma-separated list like 'grunt, elite, jackal'\n"
    "weapon: name of weapon you can see in the HUD, or 'unknown'\n"
    "suggested_action: one of move_fwd, move_back, strafe_left, strafe_right, reload, ads, fire, grenade, melee, noop\n\n"
    "Example good responses:\n"
    "  combat|grunt, elite|battle rifle|fire\n"
    "  exploration|none|assault rifle|move_fwd\n"
    "  mission_complete|none|unknown|noop\n"
    "If you can't tell, respond with: unknown|none|unknown|noop\n"
    "NO prose, NO explanation, ONE line."
)

_ANSI = re.compile(r"\u001b\[\??[0-9;]*[a-zA-Z]|\u001b\][^\u0007]*\u0007")


def strip_ansi(s: str) -> str:
    return _ANSI.sub("", s or "")


# ── DPI awareness ────────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ── Foreground check ─────────────────────────────────────
_user32 = ctypes.windll.user32


def halo_is_foreground() -> bool:
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        n = _user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        _user32.GetWindowTextW(hwnd, buf, n + 1)
        title = (buf.value or "").lower()
        return any(k in title for k in ("halo", "mcc", "master chief"))
    except Exception:
        return False


def capture_downsampled_b64(target_w: int = 640) -> str:
    """
    Screenshot, downsample to 640px wide (smaller than 896
    so prefill is faster on the vision model), JPEG-encode
    at quality 80 (smaller payload than PNG), return as
    base64 — that's what Ollama's /api/generate expects for
    multimodal `images`.
    """
    shot = pyautogui.screenshot()
    w, h = shot.size
    if w > target_w:
        scale = target_w / w
        shot = shot.resize((target_w, int(h * scale)), Image.BILINEAR)
    buf = io.BytesIO()
    shot.convert("RGB").save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ask_vision(img_b64: str, timeout_s: int = 90) -> dict:
    """
    Send the base64-encoded image to Ollama via HTTP API with
    keep_alive so the vision model stays warm in VRAM between
    calls. Massively faster than `ollama run` subprocess
    because there's no cold load per tick.
    """
    t0 = time.time()
    payload = {
        "model":      VISION_MODEL,
        "prompt":     PROMPT,
        "images":     [img_b64],
        "stream":     False,
        "keep_alive": KEEP_ALIVE,
        "options": {
            "temperature": 0.1,
            "num_predict": 80,  # short pipe-delimited response, cap tokens
        },
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"http {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

    raw = strip_ansi(str(data.get("response", ""))).strip()
    return {
        "ok": True,
        "raw": raw[:400],
        "elapsedMs": int((time.time() - t0) * 1000),
        "model_load_ms": data.get("load_duration", 0) // 1_000_000,
        "eval_count": data.get("eval_count"),
    }


def parse_vision(raw: str) -> dict:
    """Parse the pipe-delimited response into a dict."""
    if not raw:
        return {"situation": "unknown", "enemies": "none", "weapon": "unknown", "action": "noop"}
    # Find the line that looks like the expected format
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4:
            sit, ene, wep, act = parts
            return {
                "situation": sit.lower()[:32],
                "enemies":   ene.lower()[:120],
                "weapon":    wep.lower()[:32],
                "action":    act.lower()[:16],
            }
    # Fallback — no structured line found
    return {
        "situation": "unknown",
        "enemies":   "none",
        "weapon":    "unknown",
        "action":    "noop",
        "_parse":    "fallback",
    }


def notify_mission_complete() -> dict:
    """Fire POST /api/halo/missions/complete to KenAI."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{KENAI_BASE}/api/halo/missions/complete?notes=auto-detected+from+vision",
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"ok": True, "http": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_loop(interval_s: int, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(out_path, "a", encoding="utf-8", buffering=1)
    ticks = 0
    missed = 0
    print(f"[vision_observe] loop every {interval_s}s, writing to {out_path}")
    print(f"[vision_observe] drop {STOP_FLAG.name} to stop")
    try:
        while True:
            if STOP_FLAG.exists():
                print("[vision_observe] STOP flag seen")
                try: STOP_FLAG.unlink()
                except Exception: pass
                break
            if not halo_is_foreground():
                missed += 1
                time.sleep(min(interval_s, 4))
                continue

            img_b64 = capture_downsampled_b64()
            result = ask_vision(img_b64)
            ticks += 1

            row = {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "kind": "vision_observe",
                **result,
            }
            if result.get("ok"):
                parsed = parse_vision(result.get("raw", ""))
                row["parsed"] = parsed
                # Auto-detect mission complete
                if parsed.get("situation") == "mission_complete" or \
                   "mission complete" in result.get("raw", "").lower():
                    notify = notify_mission_complete()
                    row["mission_complete_fired"] = notify
                    print(f"[vision_observe] MISSION COMPLETE detected — notified: {notify}")

            fh.write(json.dumps(row, default=str) + "\n")
            print(f"[vision_observe] tick {ticks}: {result.get('raw','(err)')[:80]}")

            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("[vision_observe] Ctrl+C")
    finally:
        fh.close()
        print(f"[vision_observe] stopped — {ticks} ticks, {missed} skipped (not focused)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--one-shot", action="store_true")
    args = ap.parse_args()

    out_path = Path(args.out).resolve()

    if args.one_shot:
        if not halo_is_foreground():
            print(json.dumps({"ok": False, "error": "halo not foreground"}))
            return 1
        img_b64 = capture_downsampled_b64()
        result = ask_vision(img_b64)
        if result.get("ok"):
            result["parsed"] = parse_vision(result.get("raw", ""))
        print(json.dumps(result, default=str))
        return 0 if result.get("ok") else 1

    return run_loop(args.interval, out_path)


if __name__ == "__main__":
    sys.exit(main())
