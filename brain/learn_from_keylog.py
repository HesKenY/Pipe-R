"""
learn_from_keylog.py — turn Ken's mGBA keystrokes into training corpus rows.

Inputs:
  - agent_mode/memories/ken-ai-latest/pokemon-keylog.jsonl — Ken's raw key events
  - agent_mode/memories/ken-ai-latest/pokemon-log.jsonl    — game-state ticks

For each "key down" event in the keylog (only captured when mGBA is focused),
find the pokemon-log tick closest to that timestamp, and emit a training pair:
  instruction: "pokemon crystal. state X. what do you press?"
  output:      the GBC button Ken actually pressed

This produces imitation-learning data — kenai learns to press what Ken pressed
given the same screen state.

Output:
  corpora/ken_gameplay/pokemon_keylog.jsonl   (alpaca-compatible)

Run:
  python brain/learn_from_keylog.py
  python brain/learn_from_keylog.py --since 2026-04-17T00:00:00Z
"""

from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYLOG = ROOT / "agent_mode" / "memories" / "ken-ai-latest" / "pokemon-keylog.jsonl"
GAMELOG = ROOT / "agent_mode" / "memories" / "ken-ai-latest" / "pokemon-log.jsonl"
OUT_DIR = ROOT / "corpora" / "ken_gameplay"
OUT_FILE = OUT_DIR / "pokemon_keylog.jsonl"

# Ken's mGBA keybind → GBC button (reverse of pokemon_do.py KEYS map)
KEY_TO_BUTTON = {
    "x": "a",
    "z": "b",
    "enter": "start",
    "return": "start",
    "backspace": "select",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
}

# Only map key-down events (not up), to avoid doubling
VALID_DIR = {"down"}

# Max time gap between keypress and nearest game-log tick, seconds
MAX_MATCH_GAP = 5.0


def parse_ts(s: str) -> float:
    # Handle "2026-04-17T03:13:07.386Z" or with +00:00
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return 0.0


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def nearest_tick(ticks_by_time: list[tuple[float, dict]], target: float) -> dict | None:
    """Binary-ish search for the nearest tick by timestamp."""
    if not ticks_by_time:
        return None
    best = None
    best_diff = float("inf")
    for t, tick in ticks_by_time:
        diff = abs(t - target)
        if diff < best_diff:
            best_diff = diff
            best = tick
        if t > target + MAX_MATCH_GAP:
            break
    if best_diff <= MAX_MATCH_GAP:
        return best
    return None


def build_instruction(tick: dict) -> str:
    activity = tick.get("activity", "unknown")
    motion = tick.get("motion", 0)
    bright = tick.get("bright", 0)
    top = (tick.get("stateTop") or "").strip()[:40]
    mid = (tick.get("stateMid") or "").strip()[:40]
    bot = (tick.get("stateBot") or "").strip()[:40]
    parts = [
        "pokemon crystal tick. ken is playing. pick ONE action from: a b start select up down left right",
        f"- activity: {activity}",
        f"- motion: {round(motion, 3)}",
        f"- brightness: {round(bright, 3)}",
    ]
    if top:
        parts.append(f"- screen text top: \"{top}\"")
    if mid:
        parts.append(f"- screen text mid: \"{mid}\"")
    if bot:
        parts.append(f"- screen text bot: \"{bot}\"")
    parts.append("action:")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO timestamp — only pairs from after this")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    since_ts = parse_ts(args.since) if args.since else 0.0

    keylog = load_jsonl(KEYLOG)
    gamelog = load_jsonl(GAMELOG)

    if not keylog:
        print(f"no keylog data at {KEYLOG}")
        print("run: POST /api/pokemon/keylog/start and play with mGBA focused")
        return 1

    # Keep only key-down events from valid keys
    key_events = []
    for ev in keylog:
        if ev.get("kind") != "key":
            continue
        if ev.get("dir") not in VALID_DIR:
            continue
        k = (ev.get("key") or "").lower()
        if k not in KEY_TO_BUTTON:
            continue
        t = parse_ts(ev.get("at", ""))
        if t < since_ts:
            continue
        key_events.append((t, KEY_TO_BUTTON[k]))

    # Build sortable game-log timeline
    ticks_by_time = []
    for tick in gamelog:
        if "action" not in tick or "activity" not in tick:
            continue
        t = parse_ts(tick.get("at", ""))
        if t > 0:
            ticks_by_time.append((t, tick))
    ticks_by_time.sort(key=lambda x: x[0])

    print(f"  keylog events (key down, mapped): {len(key_events)}")
    print(f"  gamelog ticks:                    {len(ticks_by_time)}")

    pairs = []
    for ts, button in key_events:
        tick = nearest_tick(ticks_by_time, ts)
        if not tick:
            continue
        pairs.append({
            "instruction": build_instruction(tick),
            "input": "",
            "output": button,
        })

    print(f"  matched pairs: {len(pairs)}")

    # Dedupe by exact instruction
    seen = set()
    unique = []
    for p in pairs:
        sig = hash(p["instruction"] + "|" + p["output"])
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(p)

    print(f"  unique pairs:  {len(unique)}")

    if args.dry_run:
        print("dry run — not writing")
        if unique:
            print(f"  sample:\n{json.dumps(unique[0], indent=2)}")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for p in unique:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"  wrote {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
