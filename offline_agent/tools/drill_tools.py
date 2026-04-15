"""
tools/drill_tools.py

Bridge to the halo-trainer classroom project that sits at
../halo-trainer/ (sibling of offline_agent in the Codex clone).
Lets the planner run drills, read the scoreboard, list drills,
and retry only the failures — all from a Mode 0 chat turn.

These tools spawn `node` subprocesses, so they require Mode 1+
for anything that actually runs a drill. The listing / reading
tools are Mode 0-safe because they just read JSON files.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from tools.win_subprocess import run as _run

# halo-trainer sits next to offline_agent in the Codex clone:
#   Codex/offline_agent/
#   Codex/halo-trainer/
TRAINER_ROOT = (Path(__file__).parent.parent.parent / "halo-trainer").resolve()
DRILLS_DIR   = TRAINER_ROOT / "drills"
RUNS_DIR     = TRAINER_ROOT / "runs"
CORPUS_DIR   = TRAINER_ROOT / "corpus"


def _trainer_ok() -> tuple[bool, str]:
    if not TRAINER_ROOT.is_dir():
        return False, f"halo-trainer not found at {TRAINER_ROOT}"
    if not (TRAINER_ROOT / "src" / "runner.js").exists():
        return False, "halo-trainer/src/runner.js missing"
    return True, ""


# ─── Mode 0: reads ────────────────────────────────────────

def list_drills() -> dict:
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    rows = []
    for f in sorted(DRILLS_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            rows.append({
                "id":             d.get("id"),
                "title":          d.get("title"),
                "student":        d.get("student"),
                "curriculum":     d.get("curriculum"),
                "passingPercent": d.get("passingPercent"),
            })
        except Exception as e:
            rows.append({"id": f.stem, "error": str(e)})
    return {"ok": True, "count": len(rows), "drills": rows}


def read_drill(drill_id: str) -> dict:
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    for f in DRILLS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("id") == drill_id:
            return {"ok": True, "drill": d, "file": f.name}
    return {"ok": False, "error": f"drill not found: {drill_id}"}


def read_run(drill_id: str, last_n: int = 1) -> dict:
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    path = RUNS_DIR / f"{drill_id}.jsonl"
    if not path.exists():
        return {"ok": False, "error": f"no runs for {drill_id}"}
    lines = [l for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]
    out = []
    for line in lines[-last_n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return {"ok": True, "runs": out}


def scoreboard() -> dict:
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    # Run the scoreboard script and capture stdout
    try:
        res = _run(
            ["node", "src/scoreboard.js"],
            cwd=str(TRAINER_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
        )
        return {
            "ok": res.returncode == 0,
            "stdout": (res.stdout or "")[:4000],
            "stderr": (res.stderr or "")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Mode 1+: runs ────────────────────────────────────────

def run_drill(drill_id: Optional[str] = None, timeout: int = 600) -> dict:
    """
    Fire halo-trainer's runner. If drill_id is None, runs every
    drill in drills/. With an id, runs only that one.
    """
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    args = ["node", "src/runner.js"]
    if drill_id:
        args.append(drill_id)
    try:
        res = _run(
            args,
            cwd=str(TRAINER_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        return {
            "ok":       res.returncode == 0,
            "drill_id": drill_id,
            "stdout":   (res.stdout or "")[:4000],
            "stderr":   (res.stderr or "")[:1000],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"drill timeout after {timeout}s", "drill_id": drill_id}
    except Exception as e:
        return {"ok": False, "error": str(e), "drill_id": drill_id}


def retry_failed_drills(timeout: int = 900) -> dict:
    """Re-run only the drills whose last run failed."""
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    try:
        res = _run(
            ["node", "src/retry.js"],
            cwd=str(TRAINER_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        return {
            "ok":     res.returncode == 0,
            "stdout": (res.stdout or "")[:4000],
            "stderr": (res.stderr or "")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def curated_corpus_summary() -> dict:
    """How many rows per curriculum are currently in the fine-tune feed."""
    ok, err = _trainer_ok()
    if not ok:
        return {"ok": False, "error": err}
    summary = {}
    if CORPUS_DIR.is_dir():
        for f in sorted(CORPUS_DIR.glob("*.jsonl")):
            try:
                n = sum(1 for line in f.read_text(encoding="utf-8").split("\n") if line.strip())
                summary[f.stem] = n
            except Exception as e:
                summary[f.stem] = {"error": str(e)}
    return {"ok": True, "corpus": summary, "total_rows": sum(v for v in summary.values() if isinstance(v, int))}
