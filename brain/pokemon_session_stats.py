"""
pokemon_session_stats.py — dump current Pokemon session metrics to stdout.

Reads Codex/agent_mode/memories/ken-ai-latest/pokemon-log.jsonl and the
kenai_audit.jsonl, summarizes what's happened this session.

Usage:
    python brain/pokemon_session_stats.py
    python brain/pokemon_session_stats.py --tail 100     # only last N ticks
    python brain/pokemon_session_stats.py --json         # machine-readable
"""

from __future__ import annotations
import argparse
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POKE_LOG = ROOT / "agent_mode" / "memories" / "ken-ai-latest" / "pokemon-log.jsonl"
AUDIT_LOG = ROOT / "brain" / "snapshots" / "kenai_audit.jsonl"


def load_jsonl(path: Path, tail: int | None = None) -> list[dict]:
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
    if tail:
        rows = rows[-tail:]
    return rows


def stats(tail: int | None = None) -> dict:
    ticks = load_jsonl(POKE_LOG, tail=tail)
    audit = load_jsonl(AUDIT_LOG)

    if not ticks:
        return {"error": "no pokemon-log.jsonl data"}

    # only real tick entries (not battle_review / post_mortem / errors)
    real = [t for t in ticks if "action" in t and "activity" in t]

    activities = Counter(t.get("activity", "unknown") for t in real)
    actions = Counter(t.get("action", "unknown") for t in real)
    inf_times = [t["inferenceMs"] for t in real if isinstance(t.get("inferenceMs"), (int, float))]

    # Force-B heuristic: model said 'a' but action=b AND activity=dialogue
    force_b_count = sum(
        1 for t in real
        if t.get("activity") == "dialogue"
        and t.get("action") == "b"
        and "a" in (t.get("raw") or "").lower()[:20]
    )

    # Voluntary-B: raw starts with 'b' AND action=b AND activity=dialogue
    vol_b_count = sum(
        1 for t in real
        if t.get("activity") == "dialogue"
        and t.get("action") == "b"
        and (t.get("raw") or "").strip().lower().startswith("b")
    )

    # Anti-stuck: action is a direction AND raw doesn't contain the direction
    DIRS = {"up", "down", "left", "right"}
    anti_stuck_count = sum(
        1 for t in real
        if t.get("action") in DIRS
        and not any(d in (t.get("raw") or "").lower()[:30] for d in DIRS)
    )

    # Review + post-mortem counts
    review_count = sum(1 for t in ticks if t.get("type") == "battle_review")
    postmortem_count = sum(1 for t in ticks if t.get("type") == "post_mortem")
    error_count = sum(1 for t in ticks if "error" in t)

    # Battle reviews (if any)
    reviews = [t for t in ticks if t.get("type") == "battle_review"]

    out = {
        "total_ticks": len(real),
        "first_tick_at": real[0].get("at") if real else None,
        "last_tick_at": real[-1].get("at") if real else None,
        "activities": dict(activities),
        "actions": dict(actions),
        "inference_ms": {
            "min": min(inf_times) if inf_times else None,
            "max": max(inf_times) if inf_times else None,
            "median": int(statistics.median(inf_times)) if inf_times else None,
            "sub_second_count": sum(1 for x in inf_times if x < 1000),
        },
        "rule_enforcement": {
            "force_b_on_dialogue": force_b_count,
            "voluntary_b_emission": vol_b_count,
            "anti_stuck_override": anti_stuck_count,
        },
        "learning_events": {
            "battle_reviews": review_count,
            "post_mortems": postmortem_count,
            "errors": error_count,
        },
        "recent_reviews": [
            {
                "at": r.get("at"),
                "battleNumber": r.get("battleNumber"),
                "summary": (r.get("review") or "")[:200],
            }
            for r in reviews[-3:]
        ],
        "kenai_audit_entries": len(audit),
        "audit_tier_distribution": dict(Counter(a.get("label", "unknown") for a in audit)),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=None, help="only last N ticks")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    s = stats(tail=args.tail)
    if args.json:
        print(json.dumps(s, indent=2))
        return

    if "error" in s:
        print(f"error: {s['error']}")
        return

    print(f"=== Pokemon session stats (last {s['total_ticks']} ticks) ===")
    print(f"  span: {s['first_tick_at']} → {s['last_tick_at']}")
    print()
    print(f"activities: {s['activities']}")
    print(f"actions:    {s['actions']}")
    print()
    inf = s["inference_ms"]
    print(f"inference ms: min={inf['min']}  median={inf['median']}  max={inf['max']}  sub-second={inf['sub_second_count']}")
    print()
    r = s["rule_enforcement"]
    print(f"rule enforcement fires:")
    print(f"  force-B on dialogue:  {r['force_b_on_dialogue']}")
    print(f"  voluntary B:          {r['voluntary_b_emission']}")
    print(f"  anti-stuck override:  {r['anti_stuck_override']}")
    print()
    le = s["learning_events"]
    print(f"learning events: {le['battle_reviews']} battle reviews, {le['post_mortems']} post-mortems, {le['errors']} errors")
    if s["recent_reviews"]:
        print()
        print("recent reviews:")
        for r in s["recent_reviews"]:
            print(f"  #{r['battleNumber']} @ {r['at']}: {r['summary']}")
    print()
    print(f"kenai_audit entries: {s['kenai_audit_entries']}  tiers: {s['audit_tier_distribution']}")


if __name__ == "__main__":
    main()
