"""
brain_build.py — import external context into Ken AI's brain.

Reads `brain/import_manifest.yaml` and copies each listed source
file into the brain tree. Every import is idempotent — re-running
overwrites the dest file without duplication. After all imports
complete, calls memory_retriever._rebuild_index() so FTS is fresh.

Usage:
    python brain/brain_build.py --once      # one-shot import
    python brain/brain_build.py --plan      # dry run, show what would change

Writes an import_log.jsonl row per successful import.

Safe to run while the FastAPI server is up. Takes an advisory
lock on brain/import.lock so two concurrent runs don't stomp
each other.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Allow `python brain/brain_build.py` from the project root
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("PyYAML required — run `pip install pyyaml`")
    sys.exit(2)


BRAIN_DIR     = HERE
MANIFEST_PATH = BRAIN_DIR / "import_manifest.yaml"
LOCK_PATH     = BRAIN_DIR / "import.lock"
LOG_PATH      = BRAIN_DIR / "import_log.jsonl"


def acquire_lock(timeout_s: int = 10) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            LOCK_PATH.touch(exist_ok=False)
            return True
        except FileExistsError:
            time.sleep(0.3)
    return False


def release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        print(f"no manifest at {MANIFEST_PATH} — nothing to import")
        return {"imports": []}
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"imports": []}


def log_import(row: dict) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception as e:
        print(f"[warn] log write failed: {e}")


def normalize_source(src: str) -> Path:
    # Sources are given relative to the offline_agent project
    # root unless they start with an absolute path marker.
    p = Path(src)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p


def copy_file(entry: dict, dry_run: bool) -> dict:
    source = normalize_source(entry["source"])
    dest   = (BRAIN_DIR / entry["dest"]).resolve()
    kind   = entry.get("kind", "copy")
    tail_n = int(entry.get("tail_lines", 0) or 0)
    head_n = int(entry.get("head_bytes", 0) or 0)

    result = {
        "at":     datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "dest":   str(dest.relative_to(BRAIN_DIR)) if dest.is_relative_to(BRAIN_DIR) else str(dest),
        "kind":   kind,
        "ok":     False,
    }

    if not source.exists():
        result["error"] = "source missing"
        return result

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if tail_n > 0 and kind in ("copy", "tail"):
            # tail last N lines (decode as utf-8 best-effort)
            text = raw.decode("utf-8", errors="ignore")
            lines = text.splitlines()[-tail_n:]
            raw = ("\n".join(lines) + "\n").encode("utf-8")
        elif head_n > 0:
            raw = raw[:head_n]

        if dry_run:
            result["ok"] = True
            result["bytes"] = len(raw)
            result["dry_run"] = True
            return result

        dest.write_bytes(raw)
        result["ok"] = True
        result["bytes"] = len(raw)
    except Exception as e:
        result["error"] = str(e)
    return result


def run_imports(dry_run: bool = False) -> list[dict]:
    manifest = load_manifest()
    imports  = manifest.get("imports", [])
    if not imports:
        print("manifest has no imports")
        return []
    results = []
    for entry in imports:
        r = copy_file(entry, dry_run=dry_run)
        status = "ok" if r["ok"] else "fail"
        size   = r.get("bytes", "-")
        err    = r.get("error", "")
        marker = "(dry)" if dry_run else ""
        print(f"[{status}] {entry.get('source'):60s} -> {entry.get('dest'):40s} {size:>8} {marker} {err}")
        if not dry_run:
            log_import(r)
        results.append(r)
    return results


def rebuild_index_after_import() -> None:
    try:
        from agent_core.memory_retriever import MemoryRetriever
        m = MemoryRetriever()
        stats = m.rebuild()
        print(f"memory index rebuilt: {stats}")
    except Exception as e:
        print(f"[warn] index rebuild failed: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="brain_build — import external context")
    ap.add_argument("--once", action="store_true", help="run imports once and exit")
    ap.add_argument("--plan", action="store_true", help="dry run, show what would change")
    args = ap.parse_args()

    dry = args.plan and not args.once
    if args.once and args.plan:
        dry = True

    if not (args.once or args.plan):
        print("pick --once or --plan")
        return 1

    if not acquire_lock():
        print("could not acquire brain/import.lock — another build is running")
        return 1
    try:
        results = run_imports(dry_run=dry)
        if not dry:
            rebuild_index_after_import()
        ok_count = sum(1 for r in results if r.get("ok"))
        print(f"done — {ok_count}/{len(results)} ok")
        return 0 if ok_count == len(results) else 2
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
