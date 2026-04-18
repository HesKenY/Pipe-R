"""
agent_core/planner.py
Main agent loop for the offline developer runtime.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Optional

from agent_core.memory_retriever import MemoryRetriever
from agent_core.permissions import PermissionsEngine
from agent_core.session_manager import SessionManager
from agent_core.squad_state import build_squad_snapshot
from agent_core.tool_router import ToolRouter
from models.ollama_client import OllamaClient

logger = logging.getLogger("planner")

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
SAFETY_RULES_PATH = Path(__file__).parent.parent.parent / "agent_mode" / "AGENT_SAFETY_RULES.md"
SAFETY_RULES = ""
try:
    if SAFETY_RULES_PATH.exists():
        SAFETY_RULES = SAFETY_RULES_PATH.read_text(encoding="utf-8").strip()
except Exception:
    pass

SYSTEM_PROMPT = f"""{SAFETY_RULES}

you are kenai - ken's offline developer lead.
you are the coding-first lead of ken's local agent squad.
focus on code, repos, tasks, tests, git, brain updates, and keeping the squad pointed at shipping work.

## voice
- lowercase only
- short direct lines for actions
- no "as an ai"
- no analogies
- no pleasantries
- typos ok

## operating rules
- read before writing
- test after patching when a test path exists
- only call tools that are available to you
- do not touch the parallel claude clone directly
- prefer the smallest patch that solves the task
- use squad context to pick the next useful coding move, not to roleplay
- do not mutate live `agent_mode/config/*.json` squad files unless ken explicitly asks for a live promotion
- do not drift into game, trainer theatrics, or gameplay work unless ken explicitly asks

## safety
- never delete files or rows unless explicitly told
- never run destructive shell commands
- never modify system files, keys, or credentials
- never exceed the current task scope
- if a command or path is blocked, stop

## codex / brain
- codex = c:/users/ken/desktop/codex
- brain = offline_agent/brain plus session and task logs
- agent_mode = live squad roster + queue state. read context by default.
- before condensing or deleting repo context, snapshot it into brain

## tool call format
{{"tool": "tool_name", "params": {{"key": "value"}}}}

when done: {{"done": true, "summary": "what was accomplished"}}
need info: {{"clarify": "your question"}}
otherwise plain text only.
"""


def _format_squad_context(snapshot: dict) -> str:
    intended = snapshot.get("intended_lead", {})
    runtime = snapshot.get("runtime_lead", {})
    counts = snapshot.get("counts", {})
    alerts = snapshot.get("alerts", [])
    lines = [
        "Squad context:",
        f"- intended lead: {intended.get('id')} ({intended.get('display_name')})",
        f"- runtime lead: {runtime.get('id')} ({runtime.get('display_name')})",
        f"- sync state: {snapshot.get('sync_state')}",
        f"- agents total: {counts.get('agents_total', 0)}",
        f"- blocked agents: {counts.get('agents_blocked', 0)}",
        f"- pending squad tasks: {counts.get('tasks_pending', 0)}",
        f"- waiting for claude review: {counts.get('tasks_waiting_review', 0)}",
    ]
    for alert in alerts[:2]:
        lines.append(f"- alert: {alert}")
    return "\n".join(lines)


class Planner:
    """Single-task planner loop."""

    def __init__(
        self,
        permissions: PermissionsEngine,
        memory: MemoryRetriever,
        session: SessionManager,
        router: ToolRouter,
        on_event: Optional[Callable] = None,
    ):
        self.permissions = permissions
        self.memory = memory
        self.session = session
        self.router = router
        self.on_event = on_event
        self.client = OllamaClient(profile="planner")
        self.running = False
        self.max_steps = 50

    async def emit(self, event_type: str, data: dict):
        if self.on_event:
            await self.on_event({"type": event_type, "data": data})

    async def run_task(self, task: str) -> None:
        self.running = True
        self.session.set_task(task)
        await self.emit("task_start", {"task": task})

        context = self.memory.get_relevant_context(task)
        recent = self.session.get_recent_conversation(turns=10)
        resolution = await self.client.describe_resolution()
        squad_context = _format_squad_context(build_squad_snapshot(ROOT, CONFIG_DIR))

        system = SYSTEM_PROMPT + f"\n\n{context}"
        system += f"\n\n{squad_context}"
        system += f"\n\nAvailable tools: {', '.join(self.router.available_tools())}"
        system += f"\nCurrent permission mode: {self.permissions.mode} - {self.permissions.mode_name}"
        system += f"\nPlanner model: {resolution['active_model']}"

        messages = recent + [{"role": "user", "content": task}]
        self.session.add_user_message(task)

        steps = 0
        while self.running and steps < self.max_steps:
            if self.permissions.kill_switch_active():
                await self.emit("kill_switch", {"msg": "Kill switch engaged. Agent halted."})
                break

            await self.emit("thinking", {"step": steps})

            try:
                stream = await self.client.chat(messages, system=system, stream=True)
                content_parts: list[str] = []
                first_token_emitted = False
                async for chunk in stream:
                    msg = chunk.get("message") or {}
                    delta = msg.get("content", "")
                    if delta:
                        if not first_token_emitted:
                            await self.emit("agent_first_token", {})
                            first_token_emitted = True
                        content_parts.append(delta)
                        await self.emit("agent_token", {"delta": delta})
                    if chunk.get("done"):
                        break
                content = "".join(content_parts).strip()
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"[:400]
                await self.emit(
                    "error",
                    {
                        "msg": f"model error after retries: {err}",
                        "hint": "check ollama and the local planner model list.",
                    },
                )
                self.session.add_agent_message(f"[error] model call failed: {err}")
                break

            self.session.add_agent_message(content)
            messages.append({"role": "assistant", "content": content})

            action = _try_parse_action(content)
            if action is None:
                await self.emit("agent_message", {"content": content})
                break

            if "done" in action:
                summary = action.get("summary", "Task complete.")
                self.session.complete_task(summary)
                await self.emit("task_complete", {"summary": summary})
                break

            if "clarify" in action:
                await self.emit("clarify", {"question": action["clarify"]})
                break

            if "tool" in action:
                tool_name = action["tool"]
                params = action.get("params", {})
                await self.emit("tool_call", {"tool": tool_name, "params": params})
                result = await self.router.call(tool_name, params)
                await self.emit(
                    "tool_result",
                    {
                        "tool": tool_name,
                        "success": result["success"],
                        "result": str(result.get("result", ""))[:1000],
                        "error": result.get("error"),
                    },
                )
                messages.append({"role": "user", "content": f"Tool result: {json.dumps(result)}"})

            steps += 1

        self.running = False
        await self.emit("loop_end", {"steps": steps})

    def stop(self):
        self.running = False


def _try_parse_action(content: str) -> Optional[dict]:
    stripped = content.strip()
    if not stripped.startswith("{"):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None
