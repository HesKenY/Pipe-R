"""
Pokemon post-mortem — after a whiteout/loss, analyze what went wrong
and write a concrete fix to memory.

Reads recent pokemon-log.jsonl entries, finds the death event,
asks kenai:v1 for analysis, writes the lesson to memory.md.
"""

import json, sys, os, subprocess, re, time
from pathlib import Path
from datetime import datetime, timezone

MEM_DIR = Path(__file__).parent.parent / "memories" / "ken-ai-latest"
LOG_FILE = MEM_DIR / "pokemon-log.jsonl"
MEMORY = Path(__file__).parent / "memory.md"


def strip_ansi(s):
    s = re.sub(r"\x1b\[\??[0-9;]*[a-zA-Z]", "", str(s or ""))
    return re.sub(r"\x1b\][^\x07]*\x07", "", s).strip()


def read_recent_log(n=15):
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
    entries = []
    for l in lines[-n:]:
        try:
            entries.append(json.loads(l))
        except:
            pass
    return entries


def read_memory():
    if not MEMORY.exists():
        return ""
    return MEMORY.read_text(encoding="utf-8")[:2000]


def run_analysis(model="kenai:v1"):
    recent = read_recent_log(15)
    if not recent:
        return {"ok": False, "error": "no log entries"}

    # Find death events
    deaths = [e for e in recent if e.get("activity") == "death"]
    battle_entries = [e for e in recent if e.get("activity") == "battle"]

    actions_before = " → ".join([e.get("action", "?") for e in recent[-10:]])
    mem = read_memory()

    prompt = f"""pokemon crystal post-mortem. the player just lost a battle (whiteout).

recent actions: {actions_before}

battle context:
{json.dumps(battle_entries[-5:] if battle_entries else [], indent=1)[:800]}

current memory:
{mem[:1000]}

analyze in this format:
CAUSE: (what pokemon/move/type killed us)
MISTAKE: (what we did wrong — wrong move, wrong pokemon, underleveled?)
FIX: (specific action for next time — "grind to level X", "teach move Y", "switch to pokemon Z against type W")
TEAM_NOTE: (any team composition issue — missing type coverage?)

be specific. name pokemon, moves, types, levels."""

    t0 = time.time()
    flags = 0x08000000 if os.name == "nt" else 0
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt, capture_output=True, text=True,
        timeout=60, encoding="utf-8", errors="replace",
        creationflags=flags,
    )
    elapsed = int((time.time() - t0) * 1000)
    raw = strip_ansi(result.stdout or "")

    # Write lesson to memory
    if raw and MEMORY.exists():
        mem_text = MEMORY.read_text(encoding="utf-8")
        lesson = f"- {datetime.now().isoformat()[:19]} — post_mortem: {raw[:200]}"
        mem_text = mem_text.replace("## tactics_learned", "## tactics_learned\n" + lesson)
        MEMORY.write_text(mem_text, encoding="utf-8")

    return {
        "ok": True,
        "analysis": raw[:500],
        "elapsedMs": elapsed,
        "at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    model = "kenai:v1"
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
    r = run_analysis(model)
    print(json.dumps(r, indent=2))
