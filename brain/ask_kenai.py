"""
ask_kenai.py — guardrailed query wrapper around kenai:v3.

Sends a question to kenai:v3 via ollama, parses the response into one
of three confidence tiers, logs the (question, answer, tier) tuple for
audit, and emits structured JSON.

Usage:
  python brain/ask_kenai.py "should i delete the legacy auth folder?"
  echo "what's the cherp daily_logs schema?" | python brain/ask_kenai.py -

Output (stdout, JSON):
  {"tier": 1|2|3, "label": "confident|uncertain|defer",
   "answer": "...", "raw": "...", "elapsedMs": 1234}

Audit log (append):
  Codex/brain/snapshots/kenai_audit.jsonl
"""

from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG = ROOT / "brain" / "snapshots" / "kenai_audit.jsonl"
MODEL = "kenai:v3"

# ANSI code stripping (ollama spinner leak)
ANSI_CSI = re.compile(r"\u001b\[\??[0-9;]*[a-zA-Z]")
ANSI_OSC = re.compile(r"\u001b\][^\u0007]*\u0007")

# Tier 3 (defer): explicit refusal or high-stakes flag
TIER3_PATTERNS = [
    r"^\s*no rule\b.*\bask\s+ken\b",
    r"^\s*ask\s+ken\b",
    r"^\s*no rule for this\b",
    r"high stakes",
    r"\bcmc decision\b",
]

# Tier 2 (uncertain): hedge prefix or guess marker in first 60 chars
TIER2_PATTERNS = [
    r"^\s*not\s+sure\b",
    r"^\s*no rule\b",
    r"^\s*guessing\b",
    r"^\s*probably\b",
    r"\bi['']d\s+guess\b",
    r"\bdon['']t\s+quote\s+me\b",
    r"\bflag\s+if\s+wrong\b",
]

TIER_LABELS = {1: "confident", 2: "uncertain", 3: "defer"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_ansi(s: str) -> str:
    return ANSI_OSC.sub("", ANSI_CSI.sub("", s)).strip()


def classify(answer: str) -> int:
    head = answer[:200].lower()
    for p in TIER3_PATTERNS:
        if re.search(p, head):
            return 3
    for p in TIER2_PATTERNS:
        if re.search(p, head):
            return 2
    return 1


def call_kenai(question: str, timeout: int = 60) -> tuple[str, int]:
    t0 = time.time()
    proc = subprocess.run(
        ["ollama", "run", MODEL],
        input=question,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    if proc.returncode != 0:
        raise RuntimeError(f"ollama failed: {proc.stderr.strip()[:200]}")
    return strip_ansi(proc.stdout), elapsed_ms


def log_audit(entry: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", help="question for kenai:v3 (use - for stdin)")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--quiet", action="store_true", help="just print the answer, no JSON")
    args = ap.parse_args()

    if args.question == "-" or args.question is None:
        question = sys.stdin.read().strip()
    else:
        question = args.question.strip()

    if not question:
        print(json.dumps({"error": "empty question"}))
        return 1

    try:
        answer, elapsed_ms = call_kenai(question, timeout=args.timeout)
    except Exception as e:
        log_audit({
            "at": utc_now(), "question": question,
            "error": str(e)[:200], "model": MODEL,
        })
        print(json.dumps({"error": str(e)[:200]}))
        return 1

    tier = classify(answer)
    entry = {
        "at": utc_now(),
        "model": MODEL,
        "question": question,
        "answer": answer,
        "tier": tier,
        "label": TIER_LABELS[tier],
        "elapsedMs": elapsed_ms,
    }
    log_audit(entry)

    if args.quiet:
        print(answer)
    else:
        # Drop verbose fields from stdout output
        out = {k: entry[k] for k in ("tier", "label", "answer", "elapsedMs")}
        out["raw"] = answer
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
