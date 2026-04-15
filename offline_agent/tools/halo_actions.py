"""
tools/halo_actions.py

HTTP-callable wrappers around the halo_tools/launchers/*.bat
files + the model training pipeline. Wired into main.py under
/api/halo/* endpoints so the Halo tab in the UI can fire
them directly.

These run subprocesses — not safe to allow in Mode 0 by
default. Kill switch still wins.
"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

from tools.win_subprocess import run as _run, popen as _popen, DEVNULL

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
LAUNCHERS = PROJECT_ROOT / "halo_tools" / "launchers"
SCRIPTS   = PROJECT_ROOT / "halo_tools" / "scripts"
CORPUS    = PROJECT_ROOT / "brain" / "corpus" / "halo_tools_logs"


def _run_launcher(name: str, detached: bool = False) -> dict:
    """
    Spawn a launcher from halo_tools/launchers/ by filename.
    Uses the win_subprocess helpers which always set
    CREATE_NO_WINDOW on Windows so no cmd window pops up
    and steals focus from Halo.
    """
    bat = LAUNCHERS / name
    if not bat.exists():
        return {"ok": False, "error": f"launcher not found: {name}"}

    try:
        if detached:
            _popen(
                ["cmd", "/c", str(bat)],
                cwd=str(bat.parent),
                stdout=DEVNULL,
                stderr=DEVNULL,
                detached=True,
            )
            return {"ok": True, "launcher": name, "detached": True}
        res = _run(
            ["cmd", "/c", str(bat)],
            cwd=str(bat.parent),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "ok": res.returncode == 0,
            "launcher": name,
            "stdout": (res.stdout or "")[:2000],
            "stderr": (res.stderr or "")[:500],
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "launcher": name}


# ─── Aimbot ──────────────────────────────────────────────

def aimbot_start() -> dict:
    return _run_launcher("KEN_AIMBOT_ON.bat", detached=True)


def aimbot_stop() -> dict:
    return _run_launcher("KEN_AIMBOT_OFF.bat")


def aimbot_stats() -> dict:
    """Read aimbot.log.jsonl directly and compute summary."""
    import json
    log_path = SCRIPTS / "aimbot.log.jsonl"
    if not log_path.exists():
        return {"ok": True, "stats": None, "message": "no aimbot.log.jsonl yet"}
    try:
        rows = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        scans = [r for r in rows if r.get("kind") == "scan"]
        engages = [r for r in rows if r.get("kind") == "engage"]
        heartbeats = [r for r in rows if r.get("kind") == "heartbeat"]
        shots = sum(e.get("fired", 0) for e in engages)
        confs = [e.get("initial_conf", 0) for e in engages if e.get("initial_conf")]
        return {
            "ok": True,
            "stats": {
                "total_rows":   len(rows),
                "starts":       sum(1 for r in rows if r.get("kind") == "start"),
                "heartbeats":   len(heartbeats),
                "scans":        len(scans),
                "engagements":  len(engages),
                "total_shots":  shots,
                "avg_shots_per_engage": round(shots / max(1, len(engages)), 2),
                "conf_range":   [min(confs) if confs else 0, max(confs) if confs else 0],
                "avg_conf":     round(sum(confs) / max(1, len(confs)), 3),
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Memory hunters (self-elevating launchers) ───────────

def halo_hunt_start() -> dict:
    """Delta memory scanner — self-elevates to admin."""
    return _run_launcher("HALO_HUNT.bat", detached=True)


def halo_vision_hunt_start() -> dict:
    """Vision-assisted memory hunter — self-elevates to admin."""
    return _run_launcher("HALO_VISION_HUNT.bat", detached=True)


# ─── Pipe-R halo agent stack control ────────────────────

def pipe_r_halo_on() -> dict:
    """Kick the Pipe-R halo agent stack via the controller."""
    return _run_launcher("KEN_AI_HALO_ON.bat")


def pipe_r_halo_off() -> dict:
    return _run_launcher("KEN_AI_HALO_OFF.bat")


def pipe_r_halo_control() -> dict:
    """Open the halo control TUI in a new window."""
    return _run_launcher("KEN_AI_HALO_CONTROL.bat", detached=True)


# ─── Halo model training pipeline ────────────────────────

def halo_training_run(design_slug: str = "ken-ai-offline-v0") -> dict:
    """
    Full halo-to-ken-ai training pipeline:
      1. brain_build.py --once           (pull fresh halo corpus)
      2. model_designer.py full <slug>   (validate + dataset + spec)
      3. modelfile_builder.py <slug>     (emit ollama modelfile)

    Returns a report with timings + outputs. Caller (UI) should
    follow with `ollama create ken-ai-v1 -f <path>` to land the
    actual model tag — this function stops at modelfile emit so
    an aborted pipeline doesn't leave Ollama in a bad state.
    """
    results = {"started_at": datetime.now().isoformat(timespec="seconds"), "steps": []}
    root = str(PROJECT_ROOT)

    def _step(name: str, args: list[str], timeout: int = 300) -> dict:
        t0 = time.time()
        try:
            r = _run(
                args,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = round(time.time() - t0, 1)
            return {
                "step":      name,
                "ok":        r.returncode == 0,
                "elapsed_s": elapsed,
                "stdout":    (r.stdout or "")[:2000],
                "stderr":    (r.stderr or "")[:500],
            }
        except subprocess.TimeoutExpired:
            return {"step": name, "ok": False, "error": f"timeout {timeout}s"}
        except Exception as e:
            return {"step": name, "ok": False, "error": str(e)}

    # 1. refresh brain imports (halo corpus + training log tail)
    results["steps"].append(_step(
        "brain_build",
        ["python", "brain/brain_build.py", "--once"],
        timeout=120,
    ))
    if not results["steps"][-1].get("ok"):
        results["ok"] = False
        return results

    # 2. validate + build dataset + emit spec
    results["steps"].append(_step(
        "model_designer_full",
        ["python", "brain/model_designer.py", "full", design_slug],
        timeout=300,
    ))
    if not results["steps"][-1].get("ok"):
        results["ok"] = False
        return results

    # 3. emit modelfile with priming rows
    results["steps"].append(_step(
        "modelfile_builder",
        ["python", "brain/modelfile_builder.py", design_slug, "--name", f"{design_slug.replace('-', '')}v1"],
        timeout=120,
    ))

    ok = all(s.get("ok") for s in results["steps"])
    results["ok"] = ok
    results["ended_at"] = datetime.now().isoformat(timespec="seconds")
    results["next_step_command"] = (
        f"ollama create {design_slug.replace('-', '')}v1 "
        f"-f brain\\training\\modelfiles\\<newest>.Modelfile"
    )
    return results


# ─── Corpus stats ────────────────────────────────────────

def halo_corpus_stats() -> dict:
    """Count rows per imported halo log."""
    out = {"logs": {}}
    if CORPUS.is_dir():
        for f in sorted(CORPUS.glob("*.jsonl")):
            try:
                n = sum(1 for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
                out["logs"][f.name] = n
            except Exception as e:
                out["logs"][f.name] = {"error": str(e)}
    out["total_rows"] = sum(v for v in out["logs"].values() if isinstance(v, int))
    return out
