"""
agent_core/session_manager.py
Manages session lifecycle: logs, summaries, task tracking, and action history.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("session")

ROOT = Path(__file__).parent.parent
SESSIONS_DIR = ROOT / "brain" / "sessions"
TASKS_OPEN = ROOT / "tasks" / "open"
TASKS_DONE = ROOT / "tasks" / "done"
ACTION_LOG = ROOT / "logs" / "actions.jsonl"


class SessionManager:
    """
    Tracks the current session: messages, tool calls, task state, and session logs.
    Writes durable logs to disk after each turn.
    """

    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        TASKS_OPEN.mkdir(parents=True, exist_ok=True)
        TASKS_DONE.mkdir(parents=True, exist_ok=True)
        ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)

        self.session_date = datetime.now().strftime("%Y-%m-%d")
        self.session_start = datetime.now().isoformat()
        self.log_path = SESSIONS_DIR / f"{self.session_date}_session.md"
        self.conversation: list[dict] = []
        self.actions: list[dict] = []
        self.current_task: Optional[str] = None
        self.step_count = 0

        self._init_session_log()

    def _init_session_log(self):
        if not self.log_path.exists():
            self.log_path.write_text(
                f"# Session Log — {self.session_date}\n\nStarted: {self.session_start}\n\n---\n\n"
            )

    def add_user_message(self, content: str):
        self.conversation.append({"role": "user", "content": content})
        self._append_log(f"**USER**: {content}")

    def add_agent_message(self, content: str):
        self.conversation.append({"role": "assistant", "content": content})
        self._append_log(f"**AGENT**: {content}")

    def log_tool_call(self, tool: str, params: dict, result: str, permitted: bool):
        """Log a tool invocation to session log and action JSONL."""
        entry = {
            "ts": datetime.now().isoformat(),
            "tool": tool,
            "params": params,
            "result_preview": str(result)[:300],
            "permitted": permitted,
            "step": self.step_count,
        }
        self.actions.append(entry)
        with open(ACTION_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        status = "✓" if permitted else "✗ DENIED"
        self._append_log(f"  [{status}] `{tool}({json.dumps(params)[:120]})`")
        self.step_count += 1

    def set_task(self, task_description: str):
        self.current_task = task_description
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_log(f"\n### Task [{ts}]: {task_description}\n")

    def complete_task(self, summary: str):
        if self.current_task:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = self.current_task[:40].replace(" ", "_").replace("/", "_")
            done_path = TASKS_DONE / f"{ts}_{slug}.md"
            done_path.write_text(
                f"# Task: {self.current_task}\n\nCompleted: {datetime.now().isoformat()}\n\n## Summary\n{summary}\n"
            )
            self._append_log(f"\n**Task Complete**: {summary}\n---\n")
        self.current_task = None
        self.step_count = 0

    def create_task(self, title: str, description: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = title[:40].replace(" ", "_")
        task_path = TASKS_OPEN / f"{ts}_{slug}.md"
        task_path.write_text(
            f"# {title}\n\nCreated: {datetime.now().isoformat()}\n\n## Description\n{description}\n"
        )
        return str(task_path)

    def list_open_tasks(self) -> list[str]:
        return [f.name for f in TASKS_OPEN.glob("*.md")]

    def get_recent_conversation(self, turns: int = 20) -> list[dict]:
        """Return last N conversation turns for context injection."""
        return self.conversation[-turns * 2:]

    def _append_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        with open(self.log_path, "a") as f:
            f.write(f"[{ts}] {text}\n")

    def write_summary(self, summary: str):
        summaries_dir = ROOT / "brain" / "summaries"
        summaries_dir.mkdir(exist_ok=True)
        path = summaries_dir / f"{self.session_date}_summary.md"
        path.write_text(
            f"# Session Summary — {self.session_date}\n\n{summary}\n"
        )
        self._append_log(f"\n**Session Summary Written**: {path.name}")

    def get_status(self) -> dict:
        return {
            "session_date": self.session_date,
            "session_start": self.session_start,
            "current_task": self.current_task,
            "step_count": self.step_count,
            "conversation_turns": len(self.conversation) // 2,
            "actions_taken": len(self.actions),
            "open_tasks": len(self.list_open_tasks()),
        }
