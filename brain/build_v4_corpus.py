"""
Build kenai v4 training corpus.

v4 builds profile-specific corpora around the intended offline-agent goals:
  - mode discipline and tool JSON
  - BRAIN controller and task lifecycle
  - kill-switch and system-path refusal behavior
  - branch-aware Codex/Claude clone boundaries
  - CHERP/codebase/operator knowledge

Inputs:
  - latest v3 baseline: offline_agent/brain/training/modelfiles/*-kenai-v3.unsloth.jsonl (broad profile only)
  - latest canonical v3 Modelfile MESSAGE pairs
  - curated corpora: cherp, ken_voice, offline_agent, brain
  - optional pokecrystal corpus (broad profile only)
  - optional factorio corpus (broad profile only)
  - optional ken gameplay rows if present

Output:
  - offline_agent/brain/training/modelfiles/<timestamp>-kenai-v4-<profile>.unsloth.jsonl
  - brain/exports/<timestamp>-kenai-v4-<profile>.manifest.json

Format: alpaca-style {"instruction", "input", "output"} per line.
Dedupe by hash(instruction + output).

Run:
  python brain/build_v4_corpus.py
  python brain/build_v4_corpus.py --profile broad
  python brain/build_v4_corpus.py --no-write
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from build_v3_corpus import (
    CORPORA,
    EXPORTS_DIR,
    MODELFILES_DIR,
    ROOT,
    fingerprint,
    load_cherp,
    load_ken_gameplay,
    load_ken_voice,
    load_pokecrystal,
    pair,
    utc_stamp,
)


V3_MODELFILE = MODELFILES_DIR / "kenai-v3.Modelfile"
PROFILE_CHOICES = ("offline_developer", "broad")


def latest_dataset(pattern: str) -> Path | None:
    matches = sorted(MODELFILES_DIR.glob(pattern))
    if not matches:
      return None
    return matches[-1]


def load_alpaca_jsonl(path: Path | None) -> list[dict]:
    out = []
    if not path or not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "instruction" in obj and "output" in obj:
            out.append(pair(obj["instruction"], obj["output"], obj.get("input", "")))
    return out


def load_modelfile_pairs(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    msgs = re.findall(r"MESSAGE\s+(user|assistant)\s+(.+?)(?=\nMESSAGE\s+|\n#|\Z)", text, re.DOTALL)
    current_user = None
    for role, content in msgs:
        content = content.strip()
        if role == "user":
            current_user = content
        elif role == "assistant" and current_user:
            out.append(pair(current_user, content))
            current_user = None
    return out


def load_curated_json_dir(folder_name: str) -> list[dict]:
    out = []
    base = CORPORA / folder_name
    if not base.exists():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for key, value in data.items():
            if key.startswith("_") or not isinstance(value, list):
                continue
            for entry in value:
                if isinstance(entry, dict) and "instruction" in entry and "output" in entry:
                    out.append(pair(entry["instruction"], entry["output"], entry.get("input", "")))
    return out


def instruction_key(row: dict) -> str:
    return re.sub(r"\s+", " ", row["instruction"]).strip().lower()


def is_profile_doc_row(row: dict) -> bool:
    instruction = row["instruction"].strip().lower()
    return (
        instruction.startswith("# ")
        or "this file is the system prompt" in instruction
        or "personality profile" in instruction
        or "### charter" in instruction
    )


def is_pokemon_row(row: dict) -> bool:
    text = f"{row['instruction']}\n{row.get('output', '')}".lower()
    markers = [
        "pokemon",
        "crystal",
        "cyndaquil",
        "totodile",
        "chikorita",
        "lapras",
        "whitney",
        "morty",
        "clair",
        "wild pidgey",
        "miltank",
        "gengar",
        "falkner",
        "bugsy",
    ]
    return any(marker in text for marker in markers)


def is_halo_row(row: dict) -> bool:
    text = f"{row['instruction']}\n{row.get('output', '')}".lower()
    markers = [
        "halo",
        "battle rifle",
        "plasma pistol",
        "energy sword",
        "jackal",
        "hunter",
        "hunters",
        "elite ",
        "elite.",
        "flood",
        "arbiter",
        "scarab",
        "warthog",
        "gravemind",
        "tartarus",
        "mcc",
        "noob combo",
    ]
    return any(marker in text for marker in markers)


def is_off_target_drill(row: dict) -> bool:
    instruction = instruction_key(row)
    if not instruction.startswith("complete drill "):
        return False
    allowed = (
        "complete drill trainer-103-",
        "complete drill trainer-104-",
        "complete drill trainer-105-",
        "complete drill trainer-106-",
        "complete drill trainer-107-",
        "complete drill trainer-108-",
    )
    return not instruction.startswith(allowed)


def is_focus_row(row: dict) -> bool:
    if is_profile_doc_row(row):
        return False
    if is_off_target_drill(row):
        return False
    if is_pokemon_row(row):
        return False
    if is_halo_row(row):
        return False
    return True


def build_sources(profile: str) -> dict[str, list[dict]]:
    if profile == "offline_developer":
        return {
            "v3_modelfile_pairs_focus": [row for row in load_modelfile_pairs(V3_MODELFILE) if is_focus_row(row)],
            "cherp": load_cherp(),
            "ken_voice": load_ken_voice(),
            "offline_agent": load_curated_json_dir("offline_agent"),
            "brain_controller": load_curated_json_dir("brain"),
            "ken_gameplay": [],
        }

    v3_baseline_path = latest_dataset("*-kenai-v3.unsloth.jsonl")
    return {
        "v3_baseline": load_alpaca_jsonl(v3_baseline_path),
        "v3_modelfile_pairs": load_modelfile_pairs(V3_MODELFILE),
        "pokecrystal": load_pokecrystal(),
        "cherp": load_cherp(),
        "ken_voice": load_ken_voice(),
        "offline_agent": load_curated_json_dir("offline_agent"),
        "brain_controller": load_curated_json_dir("brain"),
        "factorio": load_curated_json_dir("factorio"),
        "ken_gameplay": load_ken_gameplay(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=PROFILE_CHOICES, default="offline_developer")
    ap.add_argument("--no-write", action="store_true", help="dry run; don't write the jsonl")
    args = ap.parse_args()

    profile = args.profile
    v3_baseline_path = latest_dataset("*-kenai-v3.unsloth.jsonl")
    sources = build_sources(profile)

    for name, rows in sources.items():
        print(f"  loaded {len(rows):4d} rows from {name}")

    seen = set()
    seen_instructions = {}
    merged = []
    dedup_stats = {
        name: {"in": len(rows), "kept": 0, "instruction_conflicts": 0}
        for name, rows in sources.items()
    }
    for name, rows in sources.items():
        for row in rows:
            fp = fingerprint(row)
            if fp in seen:
                continue
            ikey = instruction_key(row)
            if ikey in seen_instructions:
                dedup_stats[name]["instruction_conflicts"] += 1
                continue
            seen.add(fp)
            seen_instructions[ikey] = name
            row["_source"] = name
            merged.append(row)
            dedup_stats[name]["kept"] += 1

    print(f"\n  total after dedupe: {len(merged)} rows")
    for name, stats in dedup_stats.items():
        print(f"    {name}: {stats['kept']}/{stats['in']} kept")

    stamp = utc_stamp()
    profile_slug = profile.replace("_", "-")
    out_path = MODELFILES_DIR / f"{stamp}-kenai-v4-{profile_slug}.unsloth.jsonl"
    manifest_path = EXPORTS_DIR / f"{stamp}-kenai-v4-{profile_slug}.manifest.json"
    baseline_stats = dedup_stats.get("v3_baseline", {"in": 0, "kept": 0})
    baseline_in = baseline_stats["in"]
    baseline_kept = baseline_stats["kept"]

    manifest = {
        "version": "kenai-v4",
        "profile": profile,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(merged),
        "dataset_path": str(out_path.relative_to(ROOT)),
        "baseline_path": str(v3_baseline_path.relative_to(ROOT)) if (v3_baseline_path and profile == "broad") else None,
        "baseline_rows_in": baseline_in,
        "baseline_rows_kept_after_cleanup": baseline_kept,
        "baseline_conflicts_removed": max(0, baseline_in - baseline_kept),
        "net_new_rows_vs_full_v3": max(0, len(merged) - baseline_in),
        "sources": dedup_stats,
        "format": "alpaca {instruction, input, output}",
        "build_script": "brain/build_v4_corpus.py",
        "dedupe_strategy": "exact pair first, then normalized instruction text",
        "focus_strategy": (
            "default offline_developer profile excludes pokemon-heavy, halo-heavy, and off-target drill rows"
            if profile == "offline_developer"
            else "broad profile keeps the mixed multi-domain corpus"
        ),
        "goal_alignment": [
            {
                "goal": "local-first execution, permission discipline, and safe tool use",
                "sources": (
                    ["v3_modelfile_pairs_focus", "offline_agent"]
                    if profile == "offline_developer"
                    else ["v3_baseline", "v3_modelfile_pairs", "offline_agent"]
                ),
            },
            {
                "goal": "indexed memory, task lifecycle, and BRAIN-backed logging",
                "sources": (
                    ["brain_controller", "offline_agent", "v3_modelfile_pairs_focus"]
                    if profile == "offline_developer"
                    else ["brain_controller", "offline_agent", "v3_modelfile_pairs"]
                ),
            },
            {
                "goal": "branch-aware Codex/Claude clone boundaries and repo context",
                "sources": (
                    ["offline_agent", "brain_controller", "v3_modelfile_pairs_focus"]
                    if profile == "offline_developer"
                    else ["offline_agent", "brain_controller", "v3_baseline"]
                ),
            },
            {
                "goal": "Ken voice plus honest uncertainty framing",
                "sources": (
                    ["ken_voice", "v3_modelfile_pairs_focus", "offline_agent"]
                    if profile == "offline_developer"
                    else ["ken_voice", "v3_modelfile_pairs", "offline_agent"]
                ),
            },
            {
                "goal": "CHERP shipping knowledge and real codebase gotchas",
                "sources": (
                    ["cherp", "v3_modelfile_pairs_focus"]
                    if profile == "offline_developer"
                    else ["cherp", "v3_baseline"]
                ),
            },
            {
                "goal": "stay coding-first instead of drifting into game-training domains",
                "sources": [] if profile == "offline_developer" else ["factorio", "pokecrystal"],
            },
        ],
        "notes": [
            (
                "offline_developer is the default profile because the intended model design is a local coding/operator assistant, not a mixed game tutor."
                if profile == "offline_developer"
                else "broad profile preserves the mixed multi-domain corpus for experimentation."
            ),
            (
                "offline_developer removes pokemon, halo, factorio, and gameplay rows so the default dataset stays purely coding/operator focused."
                if profile == "offline_developer"
                else "broad profile keeps optional non-coding domains available outside the default path."
            ),
            "v4 adds offline-agent operations, exact evaluation-target pairs, BRAIN controller rows, and kill-switch refusal rows.",
            "the purpose is to maintain training focus on the intended model design instead of letting side domains dominate the dataset.",
        ],
    }

    if args.no_write:
        print(f"\n[dry run] would write {len(merged)} rows to {out_path}")
        print(json.dumps(manifest, indent=2))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in merged:
            clean = {key: value for key, value in row.items() if not key.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n  wrote {out_path}")
    print(f"  wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
