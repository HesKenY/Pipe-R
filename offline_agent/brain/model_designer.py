"""
brain/model_designer.py

The Model Designer. Follows the schema in
brain/model_designs/SCHEMA.md and the Codex-side
MODEL_DESIGNER_SPEC.md.

Three responsibilities:
  1. Validate a design.json against the required-fields list.
     A design missing any required field cannot move to the
     training step.
  2. Emit a training spec — a JSON file that matches the shape
     of Codex/brain/training_specs/*.json so both ends of the
     workbench speak the same language.
  3. Build a dataset — read the design's training_sources,
     apply filters, emit a JSONL file at
     brain/training/datasets/<slug>-<timestamp>.jsonl that can
     be fed into a local fine-tune job.

Run:
    python brain/model_designer.py validate <slug>
    python brain/model_designer.py spec     <slug>
    python brain/model_designer.py dataset  <slug>
    python brain/model_designer.py full     <slug>   # validate + spec + dataset
    python brain/model_designer.py list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE         = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DESIGNS_DIR  = HERE / "model_designs"
SPECS_DIR    = HERE / "training" / "specs"
DATASET_DIR  = HERE / "training" / "datasets"
SCHEMA_DOC   = DESIGNS_DIR / "SCHEMA.md"

REQUIRED_FIELDS = [
    "slug", "name", "mission", "capabilities", "permissions",
    "memory_strategy", "training_sources", "evaluation_goals",
    "runtime_plan", "rollout_risks",
]

SPECS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)


# ─── loader ──────────────────────────────────────────────

def design_path(slug: str) -> Path:
    return DESIGNS_DIR / slug / "design.json"


def load_design(slug: str) -> dict:
    p = design_path(slug)
    if not p.exists():
        raise FileNotFoundError(f"no design at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_design(slug: str, design: dict) -> None:
    p = design_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    design["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p.write_text(json.dumps(design, indent=2), encoding="utf-8")

    # append a revision row
    rev = p.parent / "revisions.jsonl"
    row = {
        "at": design["updated"],
        "status": design.get("status", "draft"),
        "version": design.get("version"),
    }
    with rev.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def list_designs() -> list[dict]:
    out = []
    if not DESIGNS_DIR.is_dir():
        return out
    for sub in sorted(DESIGNS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        p = sub / "design.json"
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "slug":    d.get("slug", sub.name),
                "name":    d.get("name"),
                "version": d.get("version"),
                "status":  d.get("status"),
                "updated": d.get("updated"),
            })
        except Exception as e:
            out.append({"slug": sub.name, "error": str(e)})
    return out


# ─── validate ────────────────────────────────────────────

def validate(design: dict) -> dict:
    missing = []
    empty = []
    for field in REQUIRED_FIELDS:
        if field not in design:
            missing.append(field)
            continue
        val = design[field]
        if val is None:
            empty.append(field)
        elif isinstance(val, (list, dict, str)) and len(val) == 0:
            empty.append(field)

    checks = {
        "has_mission_paragraph": bool(design.get("mission") and len(design["mission"]) > 80),
        "has_capabilities":       isinstance(design.get("capabilities"), list) and len(design.get("capabilities", [])) >= 3,
        "has_kill_switch":        bool(design.get("permissions", {}).get("kill_switch")),
        "has_audit":              bool(design.get("permissions", {}).get("audit")),
        "has_never_list":         len(design.get("permissions", {}).get("never", [])) >= 1,
        "has_sources":            len(design.get("training_sources", [])) >= 1,
        "has_eval_goals":         len(design.get("evaluation_goals", [])) >= 3,
        "has_runtime_base":       bool(design.get("runtime_plan", {}).get("base")),
        "has_risks":              len(design.get("rollout_risks", [])) >= 3,
    }

    passed = sum(1 for v in checks.values() if v)
    total  = len(checks)
    ok = not missing and not empty and passed == total

    return {
        "ok":       ok,
        "missing":  missing,
        "empty":    empty,
        "checks":   checks,
        "score":    f"{passed}/{total}",
    }


# ─── training spec ───────────────────────────────────────

def build_training_spec(design: dict, dataset_path: Path, dataset_stats: dict) -> dict:
    """
    Match the shape of Codex/brain/training_specs/*.json so
    both workbenches can swap specs.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    spec = {
        "savedAt": now,
        "name":    design["name"],
        "source":  design.get("source", "offline_agent"),
        "mission": design["mission"],
        "capabilities": design["capabilities"],
        "permissions": [
            design["permissions"].get("profile", "full-trust local mode"),
            "kill switch enforced" if design["permissions"].get("kill_switch") else "no kill switch",
            "audited" if design["permissions"].get("audit") else "unaudited",
        ],
        "dataset": {
            "name":        design["name"],
            "generatedAt": now,
            "datasetFile": str(dataset_path),
            "datasetFileRelative": str(dataset_path.relative_to(PROJECT_ROOT)),
            "filters":     {},  # filled in per-source below
            "recordCount": dataset_stats.get("total", 0),
            "sourcesCount": len(design.get("training_sources", [])),
            "bySource":    dataset_stats.get("by_source", {}),
            "kinds":       dataset_stats.get("by_kind", {}),
        },
        "runtimePlan": (
            design.get("runtime_plan", {}).get("deployment", "")
            + " — " + design.get("runtime_plan", {}).get("base", "")
        ).strip(" —"),
        "evaluationGoals": design["evaluation_goals"],
        "rolloutRisks":    design.get("rollout_risks", []),
        "memoryStrategy":  design.get("memory_strategy", {}),
        "dreamStrategy":   design.get("dream_strategy", {}),
    }
    return spec


def save_spec(design: dict, spec: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    fn = f"{ts}-{design['slug']}.json"
    path = SPECS_DIR / fn
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


# ─── dataset builder ─────────────────────────────────────

def _load_jsonl_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _apply_filter(rows: list[dict], filter_str: str) -> list[dict]:
    """Tiny filter DSL — supports AND and ==."""
    if not filter_str or filter_str.lower() == "always include":
        return rows
    # Normalize operator spellings
    f = filter_str.replace(" AND ", " and ")
    terms = [t.strip() for t in f.split(" and ")]
    out = []
    for r in rows:
        keep = True
        for term in terms:
            if "==" not in term:
                continue
            key, val = [s.strip() for s in term.split("==", 1)]
            val = val.strip("'\"")
            if val.lower() in ("true", "false"):
                want = val.lower() == "true"
            else:
                want = val
            # support nested keys with dot notation
            actual: Any = r
            for part in key.split("."):
                if isinstance(actual, dict) and part in actual:
                    actual = actual[part]
                else:
                    actual = None
                    break
            if actual != want:
                keep = False
                break
        if keep:
            out.append(r)
    return out


def _read_narrative_sources(pattern: str, project_root: Path, last_days: int = 30) -> list[dict]:
    """Walk markdown files matching the pattern, emit one row per file."""
    from datetime import timedelta
    cutoff = datetime.now().timestamp() - (last_days * 86400)
    out = []
    base = project_root
    # Support brain/ prefix resolution
    paths = list((PROJECT_ROOT).glob(pattern.replace("brain/", "brain/")))
    for p in paths:
        try:
            if p.stat().st_mtime < cutoff:
                continue
            out.append({
                "source": str(p.relative_to(PROJECT_ROOT)),
                "kind":   "narrative_context",
                "content": p.read_text(encoding="utf-8", errors="ignore"),
            })
        except Exception:
            continue
    return out


def build_dataset(design: dict) -> tuple[Path, dict]:
    slug = design["slug"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out_path = DATASET_DIR / f"{ts}-{slug}.jsonl"

    total = 0
    by_source: dict[str, int] = {}
    by_kind: dict[str, int] = {}

    with out_path.open("w", encoding="utf-8") as out:
        for src in design.get("training_sources", []):
            name    = src.get("name", "unknown")
            kind    = src.get("kind", "unknown")
            pattern = src.get("path", "")
            filt    = src.get("filter", "")

            if kind in ("drill_passing_rows", "dispatch_rows"):
                # JSONL glob
                matched_paths = list((PROJECT_ROOT).glob(pattern.replace("brain/", "brain/")))
                rows = []
                for p in matched_paths:
                    rows.extend(_load_jsonl_rows(p))
                rows = _apply_filter(rows, filt)
                for r in rows:
                    row = {"source": name, "kind": kind, "data": r}
                    out.write(json.dumps(row, default=str) + "\n")
                    total += 1
                by_source[name] = len(rows)

            elif kind == "narrative_context":
                rows = _read_narrative_sources(pattern, PROJECT_ROOT, last_days=30)
                for r in rows:
                    row = {"source": name, "kind": kind, "data": r}
                    out.write(json.dumps(row, default=str) + "\n")
                    total += 1
                by_source[name] = len(rows)

            elif kind == "reference_context":
                matched_paths = list((PROJECT_ROOT).glob(pattern.replace("brain/", "brain/")))
                for p in matched_paths:
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    row = {
                        "source": name,
                        "kind":   kind,
                        "data":   {
                            "path":    str(p.relative_to(PROJECT_ROOT)),
                            "content": content,
                        },
                    }
                    out.write(json.dumps(row, default=str) + "\n")
                    total += 1
                by_source[name] = len(matched_paths)

            else:
                by_source[name] = 0

            by_kind[kind] = by_kind.get(kind, 0) + by_source.get(name, 0)

    return out_path, {
        "total":     total,
        "by_source": by_source,
        "by_kind":   by_kind,
    }


# ─── cli ─────────────────────────────────────────────────

def cmd_validate(slug: str) -> int:
    design = load_design(slug)
    result = validate(design)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def cmd_spec(slug: str) -> int:
    design = load_design(slug)
    v = validate(design)
    if not v["ok"]:
        print(f"design not valid — cannot emit spec. issues:")
        print(json.dumps(v, indent=2))
        return 1
    # build dataset so spec has real stats
    ds_path, stats = build_dataset(design)
    spec = build_training_spec(design, ds_path, stats)
    p = save_spec(design, spec)
    print(f"spec written: {p.relative_to(PROJECT_ROOT)}")
    print(f"dataset:      {ds_path.relative_to(PROJECT_ROOT)}")
    print(f"records:      {stats['total']}")
    print(f"by source:    {stats['by_source']}")
    return 0


def cmd_dataset(slug: str) -> int:
    design = load_design(slug)
    ds_path, stats = build_dataset(design)
    print(f"dataset: {ds_path.relative_to(PROJECT_ROOT)}")
    print(f"records: {stats['total']}")
    print(f"by source: {stats['by_source']}")
    print(f"by kind:   {stats['by_kind']}")
    return 0


def cmd_full(slug: str) -> int:
    print("=== validate ===")
    design = load_design(slug)
    v = validate(design)
    print(json.dumps(v, indent=2))
    if not v["ok"]:
        return 1
    print("\n=== dataset ===")
    ds_path, stats = build_dataset(design)
    print(f"dataset: {ds_path.relative_to(PROJECT_ROOT)}")
    print(f"records: {stats['total']}")
    print("\n=== spec ===")
    spec = build_training_spec(design, ds_path, stats)
    p = save_spec(design, spec)
    print(f"spec: {p.relative_to(PROJECT_ROOT)}")
    return 0


def cmd_list() -> int:
    designs = list_designs()
    print(json.dumps(designs, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="model_designer")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "spec", "dataset", "full"):
        p = sp.add_parser(name)
        p.add_argument("slug")
    sp.add_parser("list")
    args = ap.parse_args()

    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "validate":
        return cmd_validate(args.slug)
    if args.cmd == "spec":
        return cmd_spec(args.slug)
    if args.cmd == "dataset":
        return cmd_dataset(args.slug)
    if args.cmd == "full":
        return cmd_full(args.slug)
    return 1


if __name__ == "__main__":
    sys.exit(main())
