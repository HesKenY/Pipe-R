"""
agent_core/session_manager.py

Tracks the current session and flushes durable logs into the
brain tree. Follows Ken's brain spec (2026-04-14):

    brain/
      sessions/
        YYYY-MM-DD/
          session_log.md     ← today's running log
      tasks/
        open/  done/

Session logs are single-file-per-day under a YYYY-MM-DD subdir
so walking the brain tree stays predictable. Tasks use the
slug-style files already in use by memory_retriever +
memory_tools — no collision with those.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("session")

ROOT         = Path(__file__).parent.parent
BRAIN        = ROOT / "brain"
SESSIONS_DIR = BRAIN / "sessions"
TASKS_OPEN   = BRAIN / "tasks" / "open"
TASKS_DONE   = BRAIN / "tasks" / "done"
ACTION_LOG   = ROOT / "logs" / "actions.jsonl"


def _slugify(text: str, max_len: int = 48) -> str:
    """Turn a free-form task title into a safe slug."""
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in "- _/":
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:max_len] or "task"


class SessionManager:
    """
    Writes per-turn entries into today's session_log.md and
    routes task lifecycle events into brain/tasks/.
    """

    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        TASKS_OPEN.mkdir(parents=True, exist_ok=True)
        TASKS_DONE.mkdir(parents=True, exist_ok=True)
        ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)

        self.session_date  = datetime.now().strftime("%Y-%m-%d")
        self.session_start = datetime.now().isoformat(timespec="seconds")
        self.day_dir       = SESSIONS_DIR / self.session_date
        self.log_path      = self.day_dir / "session_log.md"
        self.conversation: list[dict] = []
        self.actions:     list[dict] = []
        self.current_task: Optional[str]   = None
        self.current_task_slug: Optional[str] = None
        self.step_count = 0

        self._init_session_log()

    # ─── log init ───────────────────────────────────────────

    def _init_session_log(self) -> None:
        self.day_dir.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            header = (
                f"# Session log — {self.session_date}\n\n"
                f"Agent: Ken AI (offline skeleton)\n"
                f"Started: {self.session_start}\n\n"
                f"---\n"
            )
            self.log_path.write_text(header, encoding="utf-8")

    def _append(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(f"[{ts}] {text}\n")
        except Exception as e:
            logger.warning(f"session log write failed: {e}")

    # ─── conversation ───────────────────────────────────────

    def add_user_message(self, content: str) -> None:
        self.conversation.append({"role": "user", "content": content})
        self._append(f"**USER**: {content}")

    def add_agent_message(self, content: str) -> None:
        self.conversation.append({"role": "assistant", "content": content})
        # Keep the agent line short in the log — full content
        # still lives in self.conversation for replay
        preview = content if len(content) < 400 else content[:400] + "..."
        self._append(f"**AGENT**: {preview}")

    def get_recent_conversation(self, turns: int = 20) -> list[dict]:
        return self.conversation[-turns * 2:]

    # ─── tool calls ─────────────────────────────────────────

    def log_tool_call(self, tool: str, params: dict, result, permitted: bool) -> None:
        entry = {
            "ts":             datetime.now().isoformat(timespec="seconds"),
            "tool":           tool,
            "params":         params,
            "result_preview": str(result)[:300],
            "permitted":      permitted,
            "step":           self.step_count,
            "task":           self.current_task_slug,
        }
        self.actions.append(entry)
        try:
            with ACTION_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"action log write failed: {e}")

        status = "OK" if permitted else "DENIED"
        params_preview = json.dumps(params, default=str)[:120]
        self._append(f"  [{status}] `{tool}({params_preview})`")
        self.step_count += 1

    # ─── task lifecycle ─────────────────────────────────────

    def set_task(self, task_description: str) -> None:
        """
        Called by the planner at the start of a task. Stores
        the task slug and opens a new task file in brain/tasks/open/
        so the memory retriever can surface it to future turns.
        """
        self.current_task = task_description
        self.current_task_slug = _slugify(task_description)
        ts = datetime.now().strftime("%H:%M:%S")
        self._append(f"\n### TASK [{ts}]: {task_description}\n")

        # Create an open task file if one doesn't already exist
        path = TASKS_OPEN / f"{self.current_task_slug}.md"
        if not path.exists():
            body = (
                f"# TASK: {task_description}\n\n"
                f"**Created:** {datetime.now().isoformat(timespec='seconds')}\n"
                f"**Status:** open\n"
                f"**Origin:** chat turn\n\n"
                f"## Description\n\n{task_description}\n"
            )
            try:
                path.write_text(body, encoding="utf-8")
            except Exception as e:
                logger.warning(f"task file create failed: {e}")

    def complete_task(self, summary: str) -> None:
        """Move the current open task → done with a closing summary."""
        if not self.current_task_slug:
            return
        src = TASKS_OPEN / f"{self.current_task_slug}.md"
        dest = TASKS_DONE / f"{self.current_task_slug}.md"
        try:
            if src.exists():
                content = src.read_text(encoding="utf-8")
            else:
                content = f"# TASK: {self.current_task}\n\n"
            closed_at = datetime.now().isoformat(timespec="seconds")
            content += (
                f"\n\n## Closed {closed_at}\n\n{summary}\n"
            )
            dest.write_text(content, encoding="utf-8")
            if src.exists():
                src.unlink()
        except Exception as e:
            logger.warning(f"task complete failed: {e}")

        self._append(f"\n**TASK COMPLETE**: {summary}\n---\n")
        self.current_task = None
        self.current_task_slug = None
        self.step_count = 0

    def create_task(self, title: str, description: str) -> str:
        """Create a new open task file (Ken invokes, planner invokes)."""
        slug = _slugify(title)
        path = TASKS_OPEN / f"{slug}.md"
        body = (
            f"# TASK: {title}\n\n"
            f"**Created:** {datetime.now().isoformat(timespec='seconds')}\n"
            f"**Status:** open\n\n"
            f"## Description\n\n{description}\n"
        )
        path.write_text(body, encoding="utf-8")
        return str(path.relative_to(BRAIN))

    def list_open_tasks(self) -> list[str]:
        return sorted(f.stem for f in TASKS_OPEN.glob("*.md"))

    # ─── summaries ──────────────────────────────────────────

    def write_summary(self, summary: str) -> None:
        path = self.day_dir / "summary.md"
        path.write_text(
            f"# Session summary — {self.session_date}\n\n{summary}\n",
            encoding="utf-8",
        )
        self._append(f"\n**SESSION SUMMARY WRITTEN**: {path.name}")

    # ─── status ─────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "session_date":       self.session_date,
            "session_start":      self.session_start,
            "current_task":       self.current_task,
            "current_task_slug":  self.current_task_slug,
            "step_count":         self.step_count,
            "conversation_turns": len(self.conversation) // 2,
            "actions_taken":      len(self.actions),
            "open_tasks":         len(self.list_open_tasks()),
            "log_path":           str(self.log_path.relative_to(ROOT)),
        }
