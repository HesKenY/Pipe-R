"""
tools/memory_tools.py

Exposes the brain index + session log + task board to the
planner as callable tools. Lets Ken AI work its own memory
as part of normal task execution.

Mode 0+: everything here is read + own-brain-write only —
no filesystem writes outside brain/, no shell, no network.
Safe to allow in read-only mode.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from agent_core.memory_retriever import (
    MemoryRetriever, BRAIN_INDEX, SESSIONS_DIR, TASKS_OPEN, TASKS_DONE,
)

# Singleton so the FTS tables stay warm across tool calls.
_mem: Optional[MemoryRetriever] = None


def _get() -> MemoryRetriever:
    global _mem
    if _mem is None:
        _mem = MemoryRetriever()
    return _mem


# ─── reads ────────────────────────────────────────────────

def search_brain(query: str, limit: int = 5) -> dict:
    """Full-text search across brain_index + sessions + tasks."""
    m = _get()
    return {
        "brain":    m.search_brain(query, limit=limit),
        "sessions": m.search_sessions(query, limit=3),
        "tasks":    m.search_tasks(query, limit=3),
    }


def read_brain_file(filename: str) -> dict:
    m = _get()
    return {"filename": filename, "content": m.read_brain_file(filename)}


def list_brain_files() -> dict:
    m = _get()
    return {"files": m.list_brain_files()}


def list_open_tasks() -> dict:
    m = _get()
    return {"open": m.list_open_tasks()}


def read_task(name: str, status: str = "open") -> dict:
    m = _get()
    return {"status": status, "name": name, "content": m.read_task(name, status)}


def brain_stats() -> dict:
    return _get().stats()


# ─── writes (all scoped to brain/) ────────────────────────

def write_brain_file(filename: str, content: str) -> dict:
    """
    Overwrite or create a brain_index/*.md file. Rebuilds FTS.
    Only allowed for files inside brain_index/ — no path traversal.
    """
    if "/" in filename or "\\" in filename or filename.startswith("."):
        return {"ok": False, "error": "filename must be a simple <name>.md inside brain_index/"}
    if not filename.endswith(".md"):
        return {"ok": False, "error": "brain files must end in .md"}
    m = _get()
    m.write_brain_file(filename, content)
    return {"ok": True, "filename": filename, "bytes": len(content)}


def append_session_entry(heading: str, body: str) -> dict:
    """
    Append a new entry to today's session log. Creates the
    day folder and session_log.md if they don't exist yet.
    """
    day = datetime.now().strftime("%Y-%m-%d")
    folder = SESSIONS_DIR / day
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "session_log.md"
    stamp = datetime.now().strftime("%H:%M:%S")
    entry = f"\n\n## {stamp} — {heading}\n\n{body}\n"
    if not log.exists():
        header = f"# Session log — {day}\n\nAgent: Ken AI (offline)\n"
        log.write_text(header + entry, encoding="utf-8")
    else:
        with log.open("a", encoding="utf-8") as f:
            f.write(entry)
    _get().rebuild()
    return {"ok": True, "file": str(log.relative_to(folder.parent.parent)), "bytes": len(entry)}


def open_task(name: str, body: str) -> dict:
    """Create a new open task file. Name must be a simple slug."""
    if "/" in name or "\\" in name or not name:
        return {"ok": False, "error": "task name must be a simple slug"}
    path = TASKS_OPEN / f"{name}.md"
    if path.exists():
        return {"ok": False, "error": f"task already exists: {name}"}
    header = f"# TASK: {name}\n\n**Created:** {datetime.now().strftime('%Y-%m-%d')}\n**Status:** open\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body, encoding="utf-8")
    _get().rebuild()
    return {"ok": True, "name": name, "path": str(path.relative_to(path.parent.parent.parent))}


def close_task(name: str, summary: str = "") -> dict:
    """Move a task from tasks/open/ to tasks/done/ with a closing note."""
    src = TASKS_OPEN / f"{name}.md"
    if not src.exists():
        return {"ok": False, "error": f"no open task named {name}"}
    TASKS_DONE.mkdir(parents=True, exist_ok=True)
    dest = TASKS_DONE / f"{name}.md"
    content = src.read_text(encoding="utf-8")
    if summary:
        content += f"\n\n## Closed {datetime.now().isoformat(timespec='seconds')}\n\n{summary}\n"
    dest.write_text(content, encoding="utf-8")
    src.unlink()
    _get().rebuild()
    return {"ok": True, "name": name, "moved_to": "tasks/done/"}
