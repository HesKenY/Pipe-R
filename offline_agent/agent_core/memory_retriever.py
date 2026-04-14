"""
agent_core/memory_retriever.py

Searches the brain index, session logs, and task list for
relevant context. Uses SQLite FTS5 for fast search and pulls
only relevant chunks per turn so the planner prompt stays
compact.

Brain layout (Ken's spec, 2026-04-14):

    brain/
      brain_index/
        identity.md          <- always included
        rules.md             <- always included
        tech_stack.md
        project_map.md
        repo_map.md
        known_fixes.md
      sessions/
        YYYY-MM-DD/
          session_log.md
          (optional extra files the agent writes)
      tasks/
        open/
          <task-name>.md
        done/
          <task-name>.md
      training/
        training-log.jsonl  (imported from pipe-r agent_mode)
      corpus/
        *.jsonl             (imported from halo-trainer)

The retriever:
- maintains three FTS5 tables: brain_fts, session_fts, task_fts
- the first two brain files (identity + rules) are ALWAYS
  injected as baseline context regardless of the query
- the other brain files + sessions + open tasks are pulled
  via FTS per-query, top-K chunks
- rebuild is idempotent and fast (~50ms for the full pass)
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("memory")

ROOT         = Path(__file__).parent.parent
BRAIN_DIR    = ROOT / "brain"
BRAIN_INDEX  = BRAIN_DIR / "brain_index"
SESSIONS_DIR = BRAIN_DIR / "sessions"
TASKS_OPEN   = BRAIN_DIR / "tasks" / "open"
TASKS_DONE   = BRAIN_DIR / "tasks" / "done"
DB_PATH      = ROOT / "logs" / "memory.db"

# Files that ALWAYS appear in the context regardless of query.
# Identity + rules are small and load-bearing — they define
# who the agent is and what it must not do. Never skip them.
BASELINE_FILES = ["identity.md", "rules.md"]

# Chunk size limits so a single huge file can't blow the prompt.
MAX_CHUNK_BYTES      = 2800
MAX_BASELINE_BYTES   = 2800
MAX_SESSION_TAIL     = 2000


def _init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS brain_fts "
        "USING fts5(filename, content, tokenize='porter ascii')"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS session_fts "
        "USING fts5(rel_path, content, tokenize='porter ascii')"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS task_fts "
        "USING fts5(status, name, content, tokenize='porter ascii')"
    )
    conn.commit()
    return conn


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"read failed {path}: {e}")
        return ""


class MemoryRetriever:
    """
    Pulls the minimum amount of context needed for a given
    task. Baseline (identity + rules) always in. Everything
    else via FTS top-K.
    """

    def __init__(self, max_chunks: int = 5):
        self.max_chunks = max_chunks
        self.conn = _init_db()
        self._rebuild_index()

    # ─── index build ────────────────────────────────────────

    def _rebuild_index(self) -> dict:
        """
        Clear all three FTS tables and re-ingest from disk.
        Safe to call repeatedly.
        """
        self.conn.execute("DELETE FROM brain_fts")
        self.conn.execute("DELETE FROM session_fts")
        self.conn.execute("DELETE FROM task_fts")

        brain_count = 0
        if BRAIN_INDEX.is_dir():
            for md in sorted(BRAIN_INDEX.glob("*.md")):
                content = _read_text(md)
                if not content:
                    continue
                self.conn.execute(
                    "INSERT INTO brain_fts VALUES (?, ?)",
                    (md.name, content),
                )
                brain_count += 1

        session_count = 0
        if SESSIONS_DIR.is_dir():
            for md in sorted(SESSIONS_DIR.rglob("*.md")):
                content = _read_text(md)
                if not content:
                    continue
                rel = str(md.relative_to(SESSIONS_DIR)).replace("\\", "/")
                self.conn.execute(
                    "INSERT INTO session_fts VALUES (?, ?)",
                    (rel, content),
                )
                session_count += 1

        task_count = 0
        for status, folder in (("open", TASKS_OPEN), ("done", TASKS_DONE)):
            if not folder.is_dir():
                continue
            for md in sorted(folder.glob("*.md")):
                content = _read_text(md)
                if not content:
                    continue
                self.conn.execute(
                    "INSERT INTO task_fts VALUES (?, ?, ?)",
                    (status, md.stem, content),
                )
                task_count += 1

        self.conn.commit()
        summary = {
            "brain_files":   brain_count,
            "session_files": session_count,
            "task_files":    task_count,
            "built_at":      datetime.now().isoformat(timespec="seconds"),
        }
        logger.info(f"memory index rebuilt: {summary}")
        return summary

    def rebuild(self) -> dict:
        """Public alias for external callers (e.g. brain_build.py)."""
        return self._rebuild_index()

    # ─── direct reads ───────────────────────────────────────

    def list_brain_files(self) -> list[str]:
        if not BRAIN_INDEX.is_dir():
            return []
        return sorted(p.name for p in BRAIN_INDEX.glob("*.md"))

    def read_brain_file(self, filename: str) -> str:
        path = BRAIN_INDEX / filename
        if path.exists():
            return _read_text(path)
        return f"[brain file not found: {filename}]"

    def write_brain_file(self, filename: str, content: str) -> None:
        path = BRAIN_INDEX / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._rebuild_index()

    def list_open_tasks(self) -> list[dict]:
        if not TASKS_OPEN.is_dir():
            return []
        out = []
        for md in sorted(TASKS_OPEN.glob("*.md")):
            out.append({
                "name":    md.stem,
                "path":    str(md.relative_to(BRAIN_DIR)).replace("\\", "/"),
                "size":    md.stat().st_size,
                "updated": datetime.fromtimestamp(md.stat().st_mtime).isoformat(timespec="seconds"),
            })
        return out

    def read_task(self, name: str, status: str = "open") -> str:
        folder = TASKS_OPEN if status == "open" else TASKS_DONE
        path = folder / f"{name}.md"
        if path.exists():
            return _read_text(path)
        return f"[task not found: {status}/{name}]"

    def latest_session_log(self) -> Optional[str]:
        """Return the contents of the most recent session_log.md."""
        if not SESSIONS_DIR.is_dir():
            return None
        dirs = sorted((p for p in SESSIONS_DIR.iterdir() if p.is_dir()), reverse=True)
        for d in dirs:
            log = d / "session_log.md"
            if log.exists():
                return _read_text(log)
        return None

    # ─── search ─────────────────────────────────────────────

    def search_brain(self, query: str, limit: Optional[int] = None) -> list[dict]:
        k = limit or self.max_chunks
        rows = self.conn.execute(
            "SELECT filename, snippet(brain_fts, 1, '[', ']', '...', 30) "
            "FROM brain_fts WHERE brain_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, k),
        ).fetchall()
        return [{"source": r[0], "snippet": r[1]} for r in rows]

    def search_sessions(self, query: str, limit: int = 3) -> list[dict]:
        rows = self.conn.execute(
            "SELECT rel_path, snippet(session_fts, 1, '[', ']', '...', 40) "
            "FROM session_fts WHERE session_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [{"path": r[0], "snippet": r[1]} for r in rows]

    def search_tasks(self, query: str, limit: int = 3) -> list[dict]:
        rows = self.conn.execute(
            "SELECT status, name, snippet(task_fts, 2, '[', ']', '...', 30) "
            "FROM task_fts WHERE task_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [{"status": r[0], "name": r[1], "snippet": r[2]} for r in rows]

    # ─── context assembly ───────────────────────────────────

    def get_relevant_context(self, task: str) -> str:
        """
        Assemble the context string for a planner turn. Always
        includes identity + rules. Then appends:
          - top-K brain chunks matching the task
          - top-3 session hits
          - top-3 task hits
          - tail of the latest session_log.md
          - the open task list as a short roster
        """
        parts: list[str] = ["## brain baseline\n"]

        for fn in BASELINE_FILES:
            content = self.read_brain_file(fn)
            if content.startswith("[brain file not found"):
                continue
            if len(content) > MAX_BASELINE_BYTES:
                content = content[:MAX_BASELINE_BYTES] + "\n...(truncated)"
            parts.append(f"### {fn}\n{content}")

        # Brain FTS hits
        brain_hits = self.search_brain(task)
        if brain_hits:
            parts.append("\n## brain — relevant chunks")
            for h in brain_hits:
                parts.append(f"**[{h['source']}]** {h['snippet']}")

        # Session FTS hits
        session_hits = self.search_sessions(task)
        if session_hits:
            parts.append("\n## past sessions — relevant chunks")
            for h in session_hits:
                parts.append(f"**[{h['path']}]** {h['snippet']}")

        # Task FTS hits
        task_hits = self.search_tasks(task)
        if task_hits:
            parts.append("\n## tasks — relevant")
            for h in task_hits:
                parts.append(f"**[{h['status']}/{h['name']}]** {h['snippet']}")

        # Latest session tail
        latest = self.latest_session_log()
        if latest:
            tail = latest[-MAX_SESSION_TAIL:] if len(latest) > MAX_SESSION_TAIL else latest
            parts.append(f"\n## latest session tail\n{tail}")

        # Open task roster (always — it's cheap)
        open_tasks = self.list_open_tasks()
        if open_tasks:
            parts.append("\n## open tasks right now")
            for t in open_tasks:
                parts.append(f"- {t['name']} ({t['size']}B, updated {t['updated']})")

        return "\n\n".join(parts)

    # ─── diagnostics ────────────────────────────────────────

    def stats(self) -> dict:
        b = self.conn.execute("SELECT COUNT(*) FROM brain_fts").fetchone()[0]
        s = self.conn.execute("SELECT COUNT(*) FROM session_fts").fetchone()[0]
        t = self.conn.execute("SELECT COUNT(*) FROM task_fts").fetchone()[0]
        return {
            "brain_rows":   b,
            "session_rows": s,
            "task_rows":    t,
            "db_path":      str(DB_PATH),
        }
