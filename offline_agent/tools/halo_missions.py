"""
tools/halo_missions.py

Halo 2 mission progress tracker backed by
brain/corpus/mission_state.json (machine state) and
brain/brain_index/halo_missions.md (human-readable).

State transitions:
    locked → in-progress → complete

Only one mission is in-progress at a time. Starting a new
mission auto-completes nothing — you have to mark the
current one complete first or skip it.

When a mission completes, this module:
- updates mission_state.json
- appends a row to brain/corpus/mission_clears.jsonl
  (feeds training corpus)
- appends to brain/sessions/<date>/session_log.md
- stamps the celebration event into brain/sessions/<date>/halo_events.jsonl
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
BRAIN = PROJECT_ROOT / "brain"
STATE_PATH = BRAIN / "corpus" / "mission_state.json"
CLEARS_PATH = BRAIN / "corpus" / "mission_clears.jsonl"
SESSIONS_DIR = BRAIN / "sessions"

# Canonical Halo 2 mission list — matches halo_missions.md
MISSIONS = [
    {"num": 0,  "slug": "the-heretic",     "name": "The Heretic"},
    {"num": 1,  "slug": "the-armory",      "name": "The Armory"},
    {"num": 2,  "slug": "cairo-station",   "name": "Cairo Station"},
    {"num": 3,  "slug": "outskirts",       "name": "Outskirts"},
    {"num": 4,  "slug": "metropolis",      "name": "Metropolis"},
    {"num": 5,  "slug": "the-arbiter",     "name": "The Arbiter"},
    {"num": 6,  "slug": "the-oracle",      "name": "The Oracle"},
    {"num": 7,  "slug": "delta-halo",      "name": "Delta Halo"},
    {"num": 8,  "slug": "regret",          "name": "Regret"},
    {"num": 9,  "slug": "sacred-icon",     "name": "Sacred Icon"},
    {"num": 10, "slug": "quarantine-zone", "name": "Quarantine Zone"},
    {"num": 11, "slug": "gravemind",       "name": "Gravemind"},
    {"num": 12, "slug": "uprising",        "name": "Uprising"},
    {"num": 13, "slug": "high-charity",    "name": "High Charity"},
    {"num": 14, "slug": "the-great-journey","name": "The Great Journey"},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today_session_dir() -> Path:
    d = SESSIONS_DIR / datetime.now().strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_state() -> dict:
    return {
        "updated":                  _now(),
        "current_mission":          None,
        "current_started_at":       None,
        "current_deaths":           0,
        "current_aimbot_engagements": 0,
        "total_missions_complete":  0,
        "total_session_minutes":    0,
        "game_complete":            False,
        "missions": [
            {**m, "status": "locked", "started_at": None, "completed_at": None,
             "deaths": 0, "aimbot_shots": 0, "notes": ""}
            for m in MISSIONS
        ],
    }


def load_state() -> dict:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        state = _default_state()
        # First mission unlocks immediately
        state["missions"][0]["status"] = "unlocked"
        save_state(state)
        return state
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        # Corrupted state — rebuild from scratch
        state = _default_state()
        state["missions"][0]["status"] = "unlocked"
        save_state(state)
        return state


def save_state(state: dict) -> None:
    state["updated"] = _now()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _find_mission(state: dict, slug: str) -> dict | None:
    for m in state["missions"]:
        if m["slug"] == slug:
            return m
    return None


def _session_log_append(text: str) -> None:
    log = _today_session_dir() / "session_log.md"
    ts = datetime.now().strftime("%H:%M:%S")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] {text}\n")


def _halo_events_append(event: dict) -> None:
    event["at"] = _now()
    path = _today_session_dir() / "halo_events.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


# ─── public api ───────────────────────────────────────────

def get_status() -> dict:
    """Return the current mission tracker state."""
    s = load_state()
    return {
        "current_mission":          s.get("current_mission"),
        "current_started_at":       s.get("current_started_at"),
        "current_deaths":           s.get("current_deaths", 0),
        "current_aimbot_engagements": s.get("current_aimbot_engagements", 0),
        "total_missions_complete":  s.get("total_missions_complete", 0),
        "total_missions":           len(MISSIONS),
        "game_complete":            s.get("game_complete", False),
        "missions": [
            {
                "num":          m["num"],
                "slug":         m["slug"],
                "name":         m["name"],
                "status":       m["status"],
                "started_at":   m.get("started_at"),
                "completed_at": m.get("completed_at"),
                "deaths":       m.get("deaths", 0),
                "aimbot_shots": m.get("aimbot_shots", 0),
            }
            for m in s.get("missions", [])
        ],
    }


def start_mission(slug: str) -> dict:
    """Flip a mission to in-progress. If another is currently
    in-progress, that one is NOT auto-completed — caller must
    mark_complete first."""
    s = load_state()
    m = _find_mission(s, slug)
    if not m:
        return {"ok": False, "error": f"unknown mission slug: {slug}"}
    if m["status"] == "complete":
        return {"ok": False, "error": f"mission already complete: {slug}"}
    # Warn if another is in-progress but allow the swap
    for other in s["missions"]:
        if other["slug"] != slug and other["status"] == "in-progress":
            other["status"] = "unlocked"
            _session_log_append(f"**HALO**: mission paused — {other['name']}")

    m["status"] = "in-progress"
    m["started_at"] = _now()
    s["current_mission"] = slug
    s["current_started_at"] = m["started_at"]
    s["current_deaths"] = 0
    s["current_aimbot_engagements"] = 0
    save_state(s)

    _session_log_append(f"**HALO MISSION START** — {m['name']} ({slug})")
    _halo_events_append({"kind": "mission_start", "slug": slug, "name": m["name"]})
    return {"ok": True, "mission": m, "status": get_status()}


def log_death() -> dict:
    """Increment current run death counter."""
    s = load_state()
    s["current_deaths"] = int(s.get("current_deaths", 0)) + 1
    save_state(s)
    _halo_events_append({"kind": "death", "mission": s.get("current_mission")})
    return {"ok": True, "deaths": s["current_deaths"]}


def log_aimbot_engagement(shots: int = 1) -> dict:
    """Increment current aimbot engagement tally."""
    s = load_state()
    s["current_aimbot_engagements"] = int(s.get("current_aimbot_engagements", 0)) + shots
    save_state(s)
    return {"ok": True, "engagements": s["current_aimbot_engagements"]}


def mark_complete(slug: str | None = None, notes: str = "") -> dict:
    """
    Flip the current (or named) mission to complete. Captures
    run stats into the mission row + appends a victory line
    to the session log + writes to mission_clears.jsonl.
    """
    s = load_state()
    if slug is None:
        slug = s.get("current_mission")
    if not slug:
        return {"ok": False, "error": "no mission is currently in-progress"}
    m = _find_mission(s, slug)
    if not m:
        return {"ok": False, "error": f"unknown mission slug: {slug}"}
    if m["status"] == "complete":
        return {"ok": False, "error": f"mission already complete: {slug}"}

    now = _now()
    m["status"]       = "complete"
    m["completed_at"] = now
    m["deaths"]       = int(s.get("current_deaths", 0))
    m["aimbot_shots"] = int(s.get("current_aimbot_engagements", 0))
    m["notes"]        = notes

    # Compute run duration
    duration_min = 0
    if m.get("started_at"):
        try:
            start_dt = datetime.fromisoformat(m["started_at"])
            end_dt   = datetime.fromisoformat(now)
            duration_min = round((end_dt - start_dt).total_seconds() / 60, 1)
        except Exception:
            pass

    s["current_mission"] = None
    s["current_started_at"] = None
    s["current_deaths"] = 0
    s["current_aimbot_engagements"] = 0
    s["total_missions_complete"] = sum(1 for mm in s["missions"] if mm["status"] == "complete")

    # Unlock the next mission
    next_idx = m["num"] + 1
    for mm in s["missions"]:
        if mm["num"] == next_idx and mm["status"] == "locked":
            mm["status"] = "unlocked"

    # Game complete?
    if all(mm["status"] == "complete" for mm in s["missions"]):
        s["game_complete"] = True
        _session_log_append("**HALO GAME COMPLETE** — Ken beat Halo 2")
        _halo_events_append({"kind": "game_complete"})

    save_state(s)

    _session_log_append(
        f"**HALO MISSION COMPLETE** — {m['name']} "
        f"(duration={duration_min}min, deaths={m['deaths']}, "
        f"aimbot_shots={m['aimbot_shots']})"
    )
    _halo_events_append({
        "kind":         "mission_complete",
        "slug":         slug,
        "name":         m["name"],
        "duration_min": duration_min,
        "deaths":       m["deaths"],
        "aimbot_shots": m["aimbot_shots"],
        "notes":        notes,
    })

    # Append to mission_clears.jsonl for the training corpus
    CLEARS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CLEARS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "at":           now,
            "mission":      m["name"],
            "slug":         slug,
            "duration_min": duration_min,
            "deaths":       m["deaths"],
            "aimbot_shots": m["aimbot_shots"],
            "notes":        notes,
            "kind":         "mission_clear",
        }, default=str) + "\n")

    return {
        "ok":             True,
        "mission":        m,
        "duration_min":   duration_min,
        "game_complete":  s["game_complete"],
        "status":         get_status(),
    }


def skip_mission(slug: str, reason: str = "") -> dict:
    s = load_state()
    m = _find_mission(s, slug)
    if not m:
        return {"ok": False, "error": f"unknown mission slug: {slug}"}
    m["status"] = "skipped"
    m["notes"]  = reason
    # Unlock the next mission
    for mm in s["missions"]:
        if mm["num"] == m["num"] + 1 and mm["status"] == "locked":
            mm["status"] = "unlocked"
    save_state(s)
    _session_log_append(f"**HALO MISSION SKIPPED** — {m['name']} ({reason})")
    return {"ok": True, "status": get_status()}


def reset_progress() -> dict:
    """Hard reset. Used when starting a fresh campaign run."""
    state = _default_state()
    state["missions"][0]["status"] = "unlocked"
    save_state(state)
    _session_log_append("**HALO RESET** — campaign progress cleared")
    return {"ok": True, "status": get_status()}
