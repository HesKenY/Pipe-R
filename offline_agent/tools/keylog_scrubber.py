"""
tools/keylog_scrubber.py

Scans the halo keylog for obvious terminal/chat chatter and
moves those lines into a quarantine file so they don't pollute
the gameplay training corpus.

Halo gameplay keystrokes look like:
    w a s d space shift_l ctrl_l mouse1 mouse2 e r q 1 2 3 4

Terminal chatter looks like:
    c d space g i t space s t a t u s enter
    n o d e space s r c / r u n n e r . j s enter

Heuristic detection:
- Line contains a chunk of letter-keys that spell a shell command
  token (cd, ls, git, node, python, npm, curl, tasklist, pip, ...)
- Line contains the sequence "enter" after 20+ letter keys in a row
- Line mentions a file extension like ".py", ".bat", ".js", ".md"

Quarantined lines are written to a sibling .scrubbed.jsonl file
with reason, so nothing is lost — you can inspect what got
dropped and tune the filter.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

# Likely halo keylog locations — check multiple candidates
KEYLOG_CANDIDATES = [
    PROJECT_ROOT / ".." / "agent_mode" / "memories" / "ken-ai-latest" / "halo-keylog.jsonl",
    PROJECT_ROOT / "brain" / "corpus" / "halo_tools_logs" / "halo-keylog.jsonl",
]

TERMINAL_TOKENS = {
    "cd", "ls", "dir", "pwd", "git", "node", "python", "pip",
    "npm", "curl", "wget", "tasklist", "taskkill", "ollama",
    "powershell", "sudo", "ssh", "scp", "mkdir", "rmdir",
    "cat", "grep", "find", "awk", "sed", "vim", "nano",
    "echo", "which", "where", "code", "explorer", "start",
    "netstat", "kill", "ps", "top", "docker", "kubectl",
}
SHELL_EXT = re.compile(r"\.(py|bat|js|ts|tsx|md|json|yaml|yml|sh|ps1|cmd)\b")
LONG_LETTER_RUN = re.compile(r"([a-z_][,\s]*){20,}")


def load_keylog(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def row_text(row: dict) -> str:
    """Flatten whatever shape the keylog row uses into a text
    blob we can pattern-match against."""
    for key in ("keys", "text", "line", "buffer", "content"):
        v = row.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return " ".join(str(x) for x in v)
    return json.dumps(row, default=str)


def is_chatter(row: dict) -> tuple[bool, str]:
    text = row_text(row).lower()
    if not text:
        return False, ""

    # Tokens that are obvious shell commands
    words = re.findall(r"[a-z_][a-z0-9_-]*", text)
    word_set = set(words)
    hits = word_set & TERMINAL_TOKENS
    if hits:
        return True, f"shell tokens: {sorted(hits)}"

    # Long runs of letter keys followed by enter ≈ typing a command
    if "enter" in words and len(words) > 25:
        return True, "long letter run + enter"

    # File extensions being typed out
    if SHELL_EXT.search(text):
        return True, "file extension in typed content"

    return False, ""


def scrub(path: Path, dry_run: bool = False) -> dict:
    rows = load_keylog(path)
    if not rows:
        return {"ok": False, "error": f"keylog empty or missing: {path}"}

    keep = []
    dropped = []
    for row in rows:
        chatter, reason = is_chatter(row)
        if chatter:
            dropped.append({**row, "_scrubbed_reason": reason})
        else:
            keep.append(row)

    if dry_run:
        return {
            "ok":        True,
            "path":      str(path),
            "kept":      len(keep),
            "dropped":   len(dropped),
            "dry_run":   True,
            "samples":   [d.get("_scrubbed_reason") for d in dropped[:10]],
        }

    # Write quarantine file
    quarantine = path.with_suffix(".scrubbed.jsonl")
    with quarantine.open("a", encoding="utf-8") as f:
        for d in dropped:
            d["_scrubbed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            f.write(json.dumps(d, default=str) + "\n")

    # Rewrite the keylog with only kept rows
    with path.open("w", encoding="utf-8") as f:
        for k in keep:
            f.write(json.dumps(k, default=str) + "\n")

    return {
        "ok":         True,
        "path":       str(path),
        "kept":       len(keep),
        "dropped":    len(dropped),
        "quarantine": str(quarantine),
    }


def scrub_all(dry_run: bool = False) -> dict:
    results = []
    for cand in KEYLOG_CANDIDATES:
        path = cand.resolve()
        if path.exists():
            results.append(scrub(path, dry_run=dry_run))
    if not results:
        return {"ok": False, "error": "no keylog files found at known locations"}
    return {"ok": True, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="show what would be dropped without modifying files")
    ap.add_argument("--path", type=str, default=None, help="target a specific keylog file")
    args = ap.parse_args()

    if args.path:
        result = scrub(Path(args.path), dry_run=args.dry)
    else:
        result = scrub_all(dry_run=args.dry)

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
