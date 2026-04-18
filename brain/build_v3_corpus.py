"""
Build kenai v3 training corpus.

Inputs:
  - v2 baseline:   offline_agent/brain/training/modelfiles/2026-04-15T11-53-17-kenai-v1.unsloth.jsonl
  - Pokemon Crystal: corpora/pokecrystal/{type_chart,gym_leaders,starters,strategy.md}
  - CHERP code-dev: corpora/cherp/code_dev.json
  - Ken voice:     corpora/ken_voice/voice.json
  - Modelfile MESSAGE pairs (latest canonical kenai-v1.Modelfile)

Output:
  - offline_agent/brain/training/modelfiles/<timestamp>-kenai-v3.unsloth.jsonl
  - manifest at brain/exports/<timestamp>-kenai-v3.manifest.json

Format: alpaca-style {"instruction", "input", "output"} per line.
Dedupe by hash(instruction + output).

Run:
  python brain/build_v3_corpus.py
"""

from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Codex/
CORPORA = ROOT / "corpora"
MODELFILES_DIR = ROOT / "offline_agent" / "brain" / "training" / "modelfiles"
EXPORTS_DIR = ROOT / "brain" / "exports"

V2_BASELINE = MODELFILES_DIR / "2026-04-15T11-53-17-kenai-v1.unsloth.jsonl"
CANONICAL_MODELFILE = MODELFILES_DIR / "kenai-v1.Modelfile"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def pair(instruction: str, output: str, input_text: str = "") -> dict:
    return {"instruction": instruction.strip(), "input": input_text, "output": output.strip()}


def fingerprint(p: dict) -> str:
    blob = (p["instruction"] + "\n" + p["output"]).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ---------- v2 baseline ----------
def load_v2_baseline() -> list[dict]:
    out = []
    if not V2_BASELINE.exists():
        print(f"  WARN: v2 baseline missing at {V2_BASELINE}")
        return out
    for line in V2_BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if "instruction" in obj and "output" in obj:
                out.append(pair(obj["instruction"], obj["output"], obj.get("input", "")))
        except json.JSONDecodeError:
            continue
    return out


# ---------- Modelfile MESSAGE pairs ----------
def load_modelfile_pairs() -> list[dict]:
    """Extract MESSAGE user / MESSAGE assistant pairs from the canonical Modelfile."""
    out = []
    if not CANONICAL_MODELFILE.exists():
        return out
    text = CANONICAL_MODELFILE.read_text(encoding="utf-8")
    # Pattern: MESSAGE user <text>\nMESSAGE assistant <text>\n
    msgs = re.findall(r"MESSAGE\s+(user|assistant)\s+(.+?)(?=\nMESSAGE\s+|\n#|\Z)", text, re.DOTALL)
    cur_user = None
    for role, content in msgs:
        content = content.strip()
        if role == "user":
            cur_user = content
        elif role == "assistant" and cur_user:
            out.append(pair(cur_user, content))
            cur_user = None
    return out


# ---------- Pokemon Crystal corpus ----------
def load_pokecrystal() -> list[dict]:
    out = []
    pc = CORPORA / "pokecrystal"
    if not pc.exists():
        return out

    # Type chart
    tc_path = pc / "type_chart.json"
    if tc_path.exists():
        data = json.loads(tc_path.read_text(encoding="utf-8"))
        types = data["types"]
        chart = data["chart"]
        for atk in types:
            eff = chart.get(atk, {})
            supers = [d for d in types if eff.get(d, 1) == 2]
            resists = [d for d in types if eff.get(d, 1) == 0.5]
            immunes = [d for d in types if eff.get(d, 1) == 0]
            out.append(pair(
                f"In Pokemon Crystal, what does a {atk}-type move do against each defender type?",
                f"{atk} is super effective (2x) against: {', '.join(supers) or 'none'}. "
                f"Resisted (0.5x) by: {', '.join(resists) or 'none'}. "
                f"No effect (0x) on: {', '.join(immunes) or 'none'}. Neutral otherwise."
            ))
        for d in types:
            weak_to = [a for a in types if chart.get(a, {}).get(d, 1) == 2]
            resisted_by = [a for a in types if chart.get(a, {}).get(d, 1) == 0.5]
            immune_to = [a for a in types if chart.get(a, {}).get(d, 1) == 0]
            out.append(pair(
                f"What is a {d}-type Pokemon weak to in Pokemon Crystal?",
                f"{d} takes 2x from: {', '.join(weak_to) or 'no types'}. "
                f"Resists: {', '.join(resisted_by) or 'no types'}. "
                f"Immune to: {', '.join(immune_to) or 'no types'}."
            ))

    # Gym leaders
    gl_path = pc / "gym_leaders.json"
    if gl_path.exists():
        data = json.loads(gl_path.read_text(encoding="utf-8"))
        for g in data.get("johto", []):
            team_line = ", ".join(
                f"{p['species']} L{p['level']}" + (f" ({p['key_move']})" if p.get('key_move') else "")
                for p in g["team"]
            )
            out.append(pair(
                f"Tell me about {g['leader']}, the {g['city']} gym leader in Pokemon Crystal.",
                f"{g['leader']} runs the {g['city']} City gym ({g['type']}-type) and gives the {g['badge']} Badge. "
                f"Team: {team_line}. Tip: {g['tip']}"
            ))
            out.append(pair(
                f"What's the best counter for {g['leader']} in Pokemon Crystal?",
                f"{g['leader']} uses {g['type']}-type Pokemon. {g['tip']}"
            ))
            for p in g["team"]:
                if p.get("warning"):
                    out.append(pair(
                        f"What should I watch for with {g['leader']}'s {p['species']}?",
                        f"{g['leader']}'s {p['species']} (L{p['level']}): {p['warning']}"
                    ))
        for g in data.get("kanto", []):
            out.append(pair(
                f"Tell me about Kanto gym leader {g['leader']} in Pokemon Crystal.",
                f"{g['leader']} runs the {g['city']} City gym ({g['type']}-type) and gives the {g['badge']} Badge. "
                f"Headline team: {', '.join(g.get('headline_team', []))}. Tip: {g['tip']}"
            ))
        for e in data.get("elite_four", []):
            out.append(pair(
                f"Who is {e['name']} in the Pokemon Crystal Elite Four?",
                f"{e['name']} specializes in {e['type']}. Team: {', '.join(e.get('headline_team', []))}."
                + (f" {e['tip']}" if e.get('tip') else "")
            ))
        if "red_silver_top" in data:
            r = data["red_silver_top"]
            tline = ", ".join(f"{p['species']} L{p['level']}" for p in r["team"])
            out.append(pair(
                "Tell me about the Red battle on Mt. Silver in Pokemon Crystal.",
                f"{r['name']} sits at {r['location']}, the post-game superboss. Team: {tline}. {r['tip']}"
            ))

    # Starters
    s_path = pc / "starters.json"
    if s_path.exists():
        data = json.loads(s_path.read_text(encoding="utf-8"))
        for s in data["starters"]:
            evo = " → ".join(f"{e['species']} at L{e['level']}" for e in s["evolves_to"])
            out.append(pair(
                f"Tell me about the starter {s['name']} in Pokemon Crystal.",
                f"{s['name']} (#{s['dex']}) is a {s['type']}-type starter. Line: {s['name']} → {evo}. "
                f"Stat bias: {s['stat_bias']}. Early movepool: {', '.join(s['early_movepool'])}. {s['advantage']}"
            ))
        out.append(pair(
            "Which starter is easiest in Pokemon Crystal?",
            f"Difficulty ranking, easiest first: {' → '.join(data['starter_ranking_for_first_run'])}. "
            f"Cyndaquil cleans Bugsy and Jasmine; Totodile crushes the second half of Johto; Chikorita is hard mode."
        ))
        out.append(pair(
            "What does the rival pick if I take Cyndaquil/Totodile/Chikorita?",
            data["rival_starter_logic"]
        ))

    # Strategy markdown — bullet → QA
    strat = pc / "strategy.md"
    if strat.exists():
        md = strat.read_text(encoding="utf-8")
        sections = md.split("\n## ")[1:]
        for block in sections:
            lines = block.split("\n", 1)
            title = lines[0].strip().replace("_", " ")
            body = lines[1].strip() if len(lines) > 1 else ""
            bullets = [b.strip() for b in re.split(r"\n-\s+", body) if b.strip()]
            bullets = [re.sub(r"^-\s*", "", b) for b in bullets]
            if bullets:
                out.append(pair(
                    f"What are key tips for {title} in Pokemon Crystal?",
                    "\n".join(f"- {b}" for b in bullets)
                ))
    return out


# ---------- CHERP corpus ----------
def load_cherp() -> list[dict]:
    out = []
    cd = CORPORA / "cherp" / "code_dev.json"
    if cd.exists():
        data = json.loads(cd.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list):
                for entry in v:
                    if isinstance(entry, dict) and "instruction" in entry and "output" in entry:
                        out.append(pair(entry["instruction"], entry["output"]))
    return out


# ---------- Ken voice corpus ----------
def load_ken_voice() -> list[dict]:
    out = []
    kv = CORPORA / "ken_voice" / "voice.json"
    if kv.exists():
        data = json.loads(kv.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list):
                for entry in v:
                    if isinstance(entry, dict) and "instruction" in entry and "output" in entry:
                        out.append(pair(entry["instruction"], entry["output"]))
    return out


# ---------- Ken gameplay (keylog → training) ----------
def load_ken_gameplay() -> list[dict]:
    """Imitation-learning data harvested from Ken's mGBA play sessions.
    Produced by brain/learn_from_keylog.py."""
    out = []
    path = CORPORA / "ken_gameplay" / "pokemon_keylog.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "instruction" in obj and "output" in obj:
                    out.append(pair(obj["instruction"], obj["output"], obj.get("input", "")))
            except json.JSONDecodeError:
                continue
    return out


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true", help="dry run; don't write the jsonl")
    args = ap.parse_args()

    sources = {
        "v2_baseline": load_v2_baseline(),
        "modelfile_pairs": load_modelfile_pairs(),
        "pokecrystal": load_pokecrystal(),
        "cherp": load_cherp(),
        "ken_voice": load_ken_voice(),
        "ken_gameplay": load_ken_gameplay(),
    }

    for name, rows in sources.items():
        print(f"  loaded {len(rows):4d} rows from {name}")

    seen = set()
    merged = []
    dedup_stats = {k: {"in": len(v), "kept": 0} for k, v in sources.items()}
    for name, rows in sources.items():
        for p in rows:
            fp = fingerprint(p)
            if fp in seen:
                continue
            seen.add(fp)
            p["_source"] = name
            merged.append(p)
            dedup_stats[name]["kept"] += 1

    print(f"\n  total after dedupe: {len(merged)} rows")
    for name, s in dedup_stats.items():
        print(f"    {name}: {s['kept']}/{s['in']} kept")

    stamp = utc_stamp()
    out_path = MODELFILES_DIR / f"{stamp}-kenai-v3.unsloth.jsonl"
    manifest_path = EXPORTS_DIR / f"{stamp}-kenai-v3.manifest.json"

    manifest = {
        "version": "kenai-v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(merged),
        "dataset_path": str(out_path.relative_to(ROOT)),
        "sources": dedup_stats,
        "format": "alpaca {instruction, input, output}",
        "build_script": "brain/build_v3_corpus.py",
    }

    if args.no_write:
        print(f"\n[dry run] would write {len(merged)} rows to {out_path}")
        print(json.dumps(manifest, indent=2))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for p in merged:
            # strip _source before write so the jsonl stays alpaca-clean
            row = {k: v for k, v in p.items() if not k.startswith("_")}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n  wrote {out_path}")
    print(f"  wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
