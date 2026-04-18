"""
agent_core/squad_state.py

Read-only squad state helpers for the offline developer workbench.
This lets Ken V4 see the live agent roster and queue without rewriting
the shared agent_mode runtime by default.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

FINAL_TASK_STATES = {
    "approved_for_merge",
    "completed",
    "done",
    "failed",
    "cancelled",
}

ACTIVE_AGENT_STATES = {
    "running",
    "active",
    "busy",
}

PRIMARY_TRAINER_ID = "kenai:v4-offline-developer"
LEGACY_TRAINER_IDS = {"ken-ai:latest"}


def _normalize_trainer_id(value: Any) -> Any:
    if isinstance(value, str) and value in LEGACY_TRAINER_IDS | {PRIMARY_TRAINER_ID}:
        return PRIMARY_TRAINER_ID
    return value


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _load_yaml(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or fallback
    except Exception:
        return fallback


def _compact_agent(agent: dict) -> dict:
    agent_id = _normalize_trainer_id(agent.get("id"))
    model = agent.get("base") or agent.get("id")
    return {
        "id": agent_id,
        "model": model,
        "display_name": agent.get("displayName") or agent.get("id"),
        "role": agent.get("role") or "unknown",
        "team_role": agent.get("teamRole") or "party",
        "status": agent.get("status") or "unknown",
        "party_slot": agent.get("partySlot"),
        "blocked": bool(agent.get("blocked")),
        "block_reason": agent.get("blockReason"),
        "specialist_track": agent.get("specialistTrack"),
        "training_focus": agent.get("trainingFocus"),
        "last_used": agent.get("lastUsed"),
        "tasks_completed": agent.get("tasksCompleted", 0),
    }


def _compact_task(task: dict) -> dict:
    return {
        "id": task.get("id"),
        "objective": task.get("objective") or task.get("type") or "untitled task",
        "status": task.get("status") or "unknown",
        "priority": task.get("priority", 99),
        "assigned_agent": _normalize_trainer_id(task.get("assignedAgent")),
        "coordinator_agent": _normalize_trainer_id(task.get("coordinatorAgent")),
        "support_agent": _normalize_trainer_id(task.get("supportAgent")),
        "created_at": task.get("createdAt"),
        "started_at": task.get("startedAt"),
        "requires_review": bool(task.get("requiresClaudeReview")),
    }


def _sort_roster_key(agent: dict) -> tuple:
    team_role = agent.get("team_role")
    tier = 0 if team_role == "trainer" else 1 if team_role == "party" else 2
    slot = agent.get("party_slot")
    slot_num = slot if isinstance(slot, int) else 99
    return tier, slot_num, agent.get("display_name") or agent.get("id") or ""


def _sort_task_key(task: dict) -> tuple:
    return (
        task.get("priority", 99),
        task.get("created_at") or "",
        task.get("id") or "",
    )


def build_squad_snapshot(root: Path, config_dir: Path) -> dict:
    agent_mode_config = root.parent / "agent_mode" / "config"
    runtime = _load_json(agent_mode_config / "runtime.json", {})
    agents_raw = _load_json(agent_mode_config / "agents.json", [])
    tasks_raw = _load_json(agent_mode_config / "tasks.json", [])
    projects_cfg = _load_yaml(config_dir / "projects.yaml", {})
    models_cfg = _load_yaml(config_dir / "models.yaml", {})

    agent_cfg = projects_cfg.get("agent", {}) if isinstance(projects_cfg, dict) else {}
    models_section = models_cfg.get("models", {}) if isinstance(models_cfg, dict) else {}

    intended_lead_id = (
        agent_cfg.get("lead_model")
        or agent_cfg.get("squad_lead_model")
        or models_section.get("target")
        or "kenai:v4-offline-developer"
    )
    intended_lead_name = agent_cfg.get("lead_title") or "Ken V4 Offline Developer"

    roster = sorted((_compact_agent(agent) for agent in agents_raw), key=_sort_roster_key)
    current_lead_id = _normalize_trainer_id(runtime.get("trainerAgentId"))
    runtime_lead = next((agent for agent in roster if agent["id"] == current_lead_id), None)
    intended_roster_entry = next((agent for agent in roster if agent["id"] == intended_lead_id), None)

    task_status_counts = Counter(task.get("status") or "unknown" for task in tasks_raw)
    pending_tasks = [
        _compact_task(task)
        for task in tasks_raw
        if (task.get("status") or "unknown") not in FINAL_TASK_STATES
    ]
    pending_tasks.sort(key=_sort_task_key)

    role_counts = Counter(agent.get("team_role") or "unknown" for agent in roster)
    idle_agents = sum(1 for agent in roster if agent.get("status") == "idle")
    blocked_agents = [agent for agent in roster if agent.get("blocked")]
    active_agents = [
        agent for agent in roster if agent.get("status") in ACTIVE_AGENT_STATES or agent.get("blocked")
    ]

    sync_state = "aligned"
    if current_lead_id != intended_lead_id:
        sync_state = "runtime-pinned-to-legacy-lead"
    if not intended_roster_entry:
        sync_state = "roster-promotion-needed"

    alerts: list[str] = []
    if current_lead_id != intended_lead_id:
        alerts.append(
            f"agent_mode runtime still points at {current_lead_id or 'unknown'} while offline_agent targets {intended_lead_id}."
        )
    if not intended_roster_entry:
        alerts.append(
            f"agent_mode roster does not yet register {intended_lead_id}; a full live promotion needs agent_mode-side wiring."
        )
    if blocked_agents:
        alerts.append(f"{len(blocked_agents)} squad agent(s) are currently blocked.")

    return {
        "intended_lead": {
            "id": intended_lead_id,
            "display_name": intended_lead_name,
            "role": agent_cfg.get("squad_role") or "Coding-first squad lead",
            "present_in_roster": intended_roster_entry is not None,
        },
        "runtime_lead": runtime_lead
        or {
            "id": current_lead_id,
            "display_name": current_lead_id or "unknown",
            "role": "trainer",
            "team_role": "trainer",
            "status": "unknown",
            "party_slot": 0,
            "blocked": False,
            "block_reason": None,
            "specialist_track": "trainer",
            "training_focus": None,
            "last_used": None,
            "tasks_completed": 0,
        },
        "sync_state": sync_state,
        "counts": {
            "agents_total": len(roster),
            "agents_idle": idle_agents,
            "agents_active": len(active_agents),
            "agents_blocked": len(blocked_agents),
            "tasks_total": len(tasks_raw),
            "tasks_pending": len(pending_tasks),
            "tasks_waiting_review": task_status_counts.get("waiting_for_claude", 0),
            "tasks_ready_to_merge": task_status_counts.get("approved_for_merge", 0),
            "tasks_failed": task_status_counts.get("failed", 0),
        },
        "roles": dict(role_counts),
        "roster": roster,
        "queue": pending_tasks[:6],
        "alerts": alerts,
        "runtime_theme": runtime.get("theme", {}),
        "source_paths": {
            "agents": str(agent_mode_config / "agents.json"),
            "runtime": str(agent_mode_config / "runtime.json"),
            "tasks": str(agent_mode_config / "tasks.json"),
        },
    }
