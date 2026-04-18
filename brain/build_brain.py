from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BRAIN_DIR = ROOT / "brain"
DB_PATH = BRAIN_DIR / "BRAIN.db"
REPO_CONFIG_PATH = BRAIN_DIR / "repositories.json"
MAX_TEXT_BYTES = 1_500_000

EXCLUDED_MEMORY_PREFIXES = (
    "halo-",
)

ALLOWED_TEXT_SUFFIXES = {
    ".bat",
    ".cjs",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".jsx",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
CHUNKED_TEXT_SUFFIXES = {
    ".bat",
    ".cjs",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".jsx",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}
SOURCE_MIRROR_KINDS = {"source_mirror"}
SOURCE_MIRROR_SKIP_DIRS = {
    ".git",
    ".hg",
    ".next",
    ".turbo",
    "__pycache__",
    "bin",
    "build",
    "coverage",
    "debug",
    "dist",
    "node_modules",
    "obj",
    "out",
    "release",
    "temp",
    "tmp",
    "vendor",
}
CHUNK_LINE_LIMIT = 120
CHUNK_CHAR_LIMIT = 14_000


@dataclass(frozen=True)
class RepoItem:
    label: str
    root: Path
    kind: str = "workspace"
    priority: int = 50


@dataclass(frozen=True)
class SourceItem:
    repo_label: str
    repo_root: Path
    path: Path
    owner: str
    kind: str
    intent: str
    scope: str = "shared"

    @property
    def key(self) -> str:
        return format_repo_path(self.repo_label, self.path.relative_to(self.repo_root))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "repo"


def format_repo_path(repo_label: str, relative_path: Path) -> str:
    return f"{repo_label}/{relative_path.as_posix()}"


def guess_owner_from_slug(slug: str) -> str:
    if slug == "ken-ai-latest":
        return "ken_ai"
    return slug.replace("-", "_")


def default_repositories() -> list[RepoItem]:
    repos = [RepoItem(label="codex", root=ROOT.resolve(), kind="primary", priority=100)]
    claude_import = ROOT / "input" / "Claude-import"
    if claude_import.exists():
        repos.append(RepoItem(label="claude_import", root=claude_import.resolve(), kind="mirror", priority=90))
    return repos


def load_repositories() -> list[RepoItem]:
    if not REPO_CONFIG_PATH.exists():
        return default_repositories()

    try:
        raw = json.loads(read_text(REPO_CONFIG_PATH))
    except json.JSONDecodeError:
        return default_repositories()

    repos: list[RepoItem] = []
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            path_value = str(entry.get("path") or "").strip()
            if not path_value or entry.get("ingest", True) is False:
                continue
            repo_root = Path(path_value)
            if not repo_root.is_absolute():
                repo_root = (ROOT / repo_root).resolve()
            else:
                repo_root = repo_root.resolve()
            if not repo_root.exists():
                continue
            repos.append(
                RepoItem(
                    label=normalize_label(str(entry.get("label") or repo_root.name)),
                    root=repo_root,
                    kind=str(entry.get("kind") or "workspace"),
                    priority=int(entry.get("priority") or 50),
                )
            )

    if not repos:
        repos = default_repositories()

    deduped: dict[str, RepoItem] = {}
    for repo in sorted(repos, key=lambda item: (-item.priority, item.label)):
        deduped[str(repo.root)] = repo
    return list(deduped.values())


def discover_sources() -> tuple[list[RepoItem], list[SourceItem]]:
    repos = load_repositories()
    sources: list[SourceItem] = []
    for repo in repos:
        sources.extend(discover_sources_for_repo(repo))
    return repos, sources


def discover_sources_for_repo(repo: RepoItem) -> list[SourceItem]:
    sources: list[SourceItem] = []
    seen_keys: set[str] = set()

    def add(path: Path, owner: str, kind: str, intent: str, scope: str = "shared") -> None:
        if not path.exists() or not path.is_file():
            return
        if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            return
        try:
            if path.stat().st_size > MAX_TEXT_BYTES:
                return
        except OSError:
            return
        key = format_repo_path(repo.label, path.relative_to(repo.root))
        if key in seen_keys:
            return
        seen_keys.add(key)
        sources.append(
            SourceItem(
                repo_label=repo.label,
                repo_root=repo.root,
                path=path,
                owner=owner,
                kind=kind,
                intent=intent,
                scope=scope,
            )
        )

    for name, kind, intent in (
        ("AGENTS.md", "coordination_doc", "coordination"),
        ("CLAUDE.md", "repo_brief", "reference"),
        ("README.md", "repo_readme", "reference"),
        ("CLAUDE_BUILD_INSTRUCTIONS.md", "build_instructions", "workflow"),
    ):
        add(repo.root / name, "shared", kind, intent)

    claude_dir = repo.root / ".claude"
    if claude_dir.exists():
        for name, kind, intent in (
            ("SESSION_LOG.md", "session_log", "history"),
            ("MEMORY_INDEX.md", "memory_index", "memory"),
            ("CODEX_BRIEF.md", "brief", "identity"),
            ("WORKLIST.md", "worklist", "planning"),
        ):
            add(claude_dir / name, "shared", kind, intent)

        for plan_file in sorted((claude_dir / "plans").glob("*.md")):
            add(plan_file, "shared", "plan_doc", "planning")

        for command_file in sorted((claude_dir / "commands").glob("*.md")):
            add(command_file, "shared", "command_doc", "workflow")

        logs_dir = claude_dir / "logs"
        if logs_dir.exists():
            for name, owner in (
                ("codex.log", "codex"),
                ("claude.log", "claude"),
                ("shared.log", "shared"),
                ("server.log", "shared"),
                ("hub.log", "shared"),
            ):
                add(logs_dir / name, owner, "runtime_log", "runtime")

    add(repo.root / "hub.log", "shared", "runtime_log", "runtime")

    brain_dir = repo.root / "brain"
    if brain_dir.exists():
        for file in sorted(brain_dir.glob("*.md")):
            add(file, "shared", "brain_doc", "brain")
        for file in sorted(brain_dir.glob("*.json")):
            add(file, "shared", "brain_config", "brain")

    add(repo.root / "agents" / "notes.json", "shared", "agent_notes", "memory")

    training_dir = repo.root / "agent_mode" / "training"
    if training_dir.exists():
        for file in sorted(training_dir.rglob("*.jsonl")):
            add(file, "shared", "training_log", "training")

    config_dir = repo.root / "agent_mode" / "config"
    if config_dir.exists():
        for file in sorted(config_dir.glob("*.json")):
            kind, intent = classify_config_file(file.name)
            add(file, "shared", kind, intent)

    for extra_root in (repo.root / "agent_mode" / "ken", repo.root / "agents"):
        if not extra_root.exists():
            continue
        for file in sorted(extra_root.rglob("*")):
            if not file.is_file():
                continue
            kind, intent = classify_misc_text_file(file)
            if not kind:
                continue
            add(file, "shared", kind, intent)

    memories_dir = repo.root / "agent_mode" / "memories"
    if memories_dir.exists():
        for slug_dir in sorted(path for path in memories_dir.iterdir() if path.is_dir()):
            owner = guess_owner_from_slug(slug_dir.name)
            for file in sorted(slug_dir.rglob("*")):
                if not file.is_file():
                    continue
                if file.name.startswith(EXCLUDED_MEMORY_PREFIXES):
                    continue
                kind, intent = classify_memory_file(file)
                if not kind:
                    continue
                add(file, owner, kind, intent, scope="agent")

    if repo.kind in SOURCE_MIRROR_KINDS:
        for file in iter_source_mirror_files(repo.root):
            kind, intent = classify_source_mirror_file(file)
            if not kind:
                continue
            add(file, "shared", kind, intent)

    return sources


def classify_config_file(name: str) -> tuple[str, str]:
    lowered = name.lower()
    mapping = {
        "agents.json": ("agent_registry", "registry"),
        "tasks.json": ("task_registry", "tasking"),
        "runtime.json": ("runtime_config", "runtime"),
        "factory-bridge.json": ("bridge_config", "coordination"),
        "halo_training.json": ("training_config", "training"),
    }
    return mapping.get(lowered, ("agent_config", "config"))


def classify_misc_text_file(path: Path) -> tuple[str | None, str | None]:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_TEXT_SUFFIXES:
        return None, None
    name = path.name.lower()
    if suffix == ".md":
        return "project_doc", "reference"
    if suffix == ".log":
        return "runtime_log", "runtime"
    if suffix == ".jsonl":
        return "project_events", "events"
    if suffix == ".json":
        if "note" in name:
            return "project_notes", "memory"
        return "project_config", "config"
    if suffix == ".txt":
        return "project_text", "reference"
    return None, None


def iter_source_mirror_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SOURCE_MIRROR_SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            continue
        yield path


def classify_source_mirror_file(path: Path) -> tuple[str | None, str | None]:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".md":
        return ("mirror_readme", "reference") if name == "readme.md" else ("mirror_doc", "reference")
    if suffix in {".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini"}:
        return "mirror_config", "config"
    if suffix in {".sh", ".ps1", ".bat"}:
        return "mirror_script", "workflow"
    if suffix == ".sql":
        return "mirror_schema", "reference"
    if suffix in {".css", ".html", ".svg", ".xml"}:
        return "mirror_ui_source", "reference"
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"}:
        return "mirror_source_code", "reference"
    if suffix == ".txt":
        return "mirror_text", "reference"
    return None, None


def classify_memory_file(path: Path) -> tuple[str | None, str | None]:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_TEXT_SUFFIXES:
        return None, None

    lowered = path.name.lower()
    if suffix == ".md":
        if "dream" in lowered:
            return "agent_dreams", "dream"
        if "note" in lowered:
            return "agent_notes", "memory"
        return "agent_memory", "memory"
    if suffix == ".txt":
        return "agent_text", "memory"
    if suffix == ".log":
        return "agent_runtime_log", "runtime"
    if suffix == ".jsonl":
        if lowered == "dreams.jsonl":
            return "agent_dreams", "dream"
        if lowered == "learning.jsonl":
            return "agent_learning", "learning"
        if lowered == "chat-log.jsonl":
            return "agent_chat", "chat"
        return "agent_events", "events"
    if suffix == ".json":
        if "dream" in lowered:
            return "agent_dream_profile", "dream"
        if "learn" in lowered:
            return "agent_learning_state", "learning"
        if "chat" in lowered:
            return "agent_chat_state", "chat"
        return "agent_state", "memory"
    return None, None


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          path TEXT NOT NULL UNIQUE,
          repo_label TEXT NOT NULL DEFAULT 'codex',
          repo_root TEXT NOT NULL DEFAULT '',
          owner TEXT NOT NULL,
          kind TEXT NOT NULL,
          intent TEXT NOT NULL,
          scope TEXT NOT NULL,
          file_hash TEXT NOT NULL,
          file_mtime REAL NOT NULL,
          indexed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_id INTEGER NOT NULL,
          repo_label TEXT NOT NULL DEFAULT 'codex',
          repo_root TEXT NOT NULL DEFAULT '',
          owner TEXT NOT NULL,
          kind TEXT NOT NULL,
          intent TEXT NOT NULL,
          scope TEXT NOT NULL,
          title TEXT NOT NULL,
          ts TEXT,
          section TEXT,
          path TEXT NOT NULL,
          line_start INTEGER,
          line_end INTEGER,
          content TEXT NOT NULL,
          metadata_json TEXT,
          FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS branches (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          repo_label TEXT NOT NULL DEFAULT 'codex',
          repo_root TEXT NOT NULL DEFAULT '',
          name TEXT NOT NULL UNIQUE,
          branch_name TEXT NOT NULL DEFAULT '',
          is_current INTEGER NOT NULL,
          upstream TEXT,
          head_sha TEXT,
          commit_ts TEXT,
          summary TEXT,
          author TEXT,
          indexed_at TEXT NOT NULL
        );
        """
    )

    ensure_column(conn, "sources", "repo_label", "TEXT NOT NULL DEFAULT 'codex'")
    ensure_column(conn, "sources", "repo_root", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "records", "repo_label", "TEXT NOT NULL DEFAULT 'codex'")
    ensure_column(conn, "records", "repo_root", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "branches", "repo_label", "TEXT NOT NULL DEFAULT 'codex'")
    ensure_column(conn, "branches", "repo_root", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "branches", "branch_name", "TEXT NOT NULL DEFAULT ''")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_repo_label ON sources(repo_label)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_owner ON records(owner)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_intent ON records(intent)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_ts ON records(ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_path ON records(path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_repo_label ON records(repo_label)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_branches_repo_label ON branches(repo_label)")

    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
              title, content, owner, kind, intent, path,
              content='records',
              content_rowid='id'
            )
            """
        )
    except sqlite3.OperationalError:
        pass


def split_markdown_sections(text: str) -> list[tuple[str, str, int]]:
    lines = text.splitlines()
    sections: list[tuple[str, str, int]] = []
    current_title = "document"
    current_lines: list[str] = []
    current_start = 1

    for index, line in enumerate(lines, start=1):
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip(), current_start))
            current_title = line.lstrip("#").strip() or "section"
            current_lines = []
            current_start = index
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip(), current_start))

    return [(title, body, start) for title, body, start in sections if body]


def parse_timestamp(obj: dict, fallback: str | None = None) -> str | None:
    for key in ("at", "ts", "createdAt", "updatedAt", "timestamp"):
        value = obj.get(key)
        if value:
            return str(value)
    return fallback


def split_line_chunks(
    text: str,
    *,
    line_limit: int = CHUNK_LINE_LIMIT,
    char_limit: int = CHUNK_CHAR_LIMIT,
) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[tuple[int, int, str]] = []
    start_line = 1
    buffer: list[str] = []
    current_chars = 0

    for index, line in enumerate(lines, start=1):
        buffer.append(line)
        current_chars += len(line) + 1
        if len(buffer) >= line_limit or current_chars >= char_limit:
            body = "\n".join(buffer).strip()
            if body:
                chunks.append((start_line, index, body))
            buffer = []
            current_chars = 0
            start_line = index + 1

    if buffer:
        body = "\n".join(buffer).strip()
        if body:
            chunks.append((start_line, len(lines), body))

    return chunks


def build_records_for_source(source: SourceItem) -> list[dict]:
    text = read_text(source.path)
    path_str = source.key
    suffix = source.path.suffix.lower()

    if suffix in {".md", ".txt"}:
        sections = split_markdown_sections(text) if suffix == ".md" else [("document", text.strip(), 1)]
        return [
            {
                "repo_label": source.repo_label,
                "repo_root": str(source.repo_root),
                "owner": source.owner,
                "kind": source.kind,
                "intent": source.intent,
                "scope": source.scope,
                "title": title,
                "ts": None,
                "section": title,
                "path": path_str,
                "line_start": start_line,
                "line_end": None,
                "content": body,
                "metadata_json": None,
            }
            for title, body, start_line in sections
            if body
            ]

    if suffix in CHUNKED_TEXT_SUFFIXES:
        records = []
        for index, (start_line, end_line, body) in enumerate(split_line_chunks(text), start=1):
            records.append(
                {
                    "repo_label": source.repo_label,
                    "repo_root": str(source.repo_root),
                    "owner": source.owner,
                    "kind": source.kind,
                    "intent": source.intent,
                    "scope": source.scope,
                    "title": f"{source.path.name} lines {start_line}-{end_line}",
                    "ts": None,
                    "section": f"chunk_{index}",
                    "path": path_str,
                    "line_start": start_line,
                    "line_end": end_line,
                    "content": body,
                    "metadata_json": None,
                }
            )
        return records

    if suffix == ".log":
        records = []
        for index, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            ts = line[:20] if len(line) >= 20 and line[:4].isdigit() else None
            records.append(
                {
                    "repo_label": source.repo_label,
                    "repo_root": str(source.repo_root),
                    "owner": source.owner,
                    "kind": source.kind,
                    "intent": source.intent,
                    "scope": source.scope,
                    "title": f"{source.path.name} line {index}",
                    "ts": ts,
                    "section": source.path.name,
                    "path": path_str,
                    "line_start": index,
                    "line_end": index,
                    "content": line,
                    "metadata_json": None,
                }
            )
        return records

    if suffix == ".jsonl":
        records = []
        for index, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = None

            if obj is None:
                records.append(
                    {
                        "repo_label": source.repo_label,
                        "repo_root": str(source.repo_root),
                        "owner": source.owner,
                        "kind": source.kind,
                        "intent": source.intent,
                        "scope": source.scope,
                        "title": f"{source.path.name} line {index}",
                        "ts": None,
                        "section": source.path.name,
                        "path": path_str,
                        "line_start": index,
                        "line_end": index,
                        "content": line,
                        "metadata_json": None,
                    }
                )
                continue

            title_parts = [source.kind]
            for key in ("role", "pattern", "taskId", "objective", "kind"):
                if obj.get(key):
                    title_parts.append(str(obj[key]))
                    break

            records.append(
                {
                    "repo_label": source.repo_label,
                    "repo_root": str(source.repo_root),
                    "owner": source.owner,
                    "kind": source.kind,
                    "intent": source.intent,
                    "scope": source.scope,
                    "title": " | ".join(title_parts),
                    "ts": parse_timestamp(obj),
                    "section": source.path.name,
                    "path": path_str,
                    "line_start": index,
                    "line_end": index,
                    "content": json.dumps(obj, ensure_ascii=False),
                    "metadata_json": json.dumps(obj, ensure_ascii=False),
                }
            )
        return records

    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        records = []
        if isinstance(data, list):
            for index, item in enumerate(data, start=1):
                records.append(
                    {
                        "repo_label": source.repo_label,
                        "repo_root": str(source.repo_root),
                        "owner": source.owner,
                        "kind": source.kind,
                        "intent": source.intent,
                        "scope": source.scope,
                        "title": f"{source.path.name} item {index}",
                        "ts": parse_timestamp(item if isinstance(item, dict) else {}),
                        "section": source.path.name,
                        "path": path_str,
                        "line_start": None,
                        "line_end": None,
                        "content": json.dumps(item, ensure_ascii=False),
                        "metadata_json": json.dumps(item, ensure_ascii=False),
                    }
                )
        elif isinstance(data, dict):
            for key, value in data.items():
                records.append(
                    {
                        "repo_label": source.repo_label,
                        "repo_root": str(source.repo_root),
                        "owner": source.owner,
                        "kind": source.kind,
                        "intent": source.intent,
                        "scope": source.scope,
                        "title": f"{source.path.name} | {key}",
                        "ts": parse_timestamp(value if isinstance(value, dict) else {}),
                        "section": key,
                        "path": path_str,
                        "line_start": None,
                        "line_end": None,
                        "content": json.dumps(value, ensure_ascii=False),
                        "metadata_json": json.dumps(value, ensure_ascii=False),
                    }
                )
        return records

    return []


def refresh_source(conn: sqlite3.Connection, source: SourceItem) -> tuple[bool, int]:
    file_mtime = source.path.stat().st_mtime
    digest = file_hash(source.path)
    row = conn.execute("SELECT id, file_hash FROM sources WHERE path = ?", (source.key,)).fetchone()

    if row and row["file_hash"] == digest:
        conn.execute(
            "UPDATE sources SET indexed_at = ?, file_mtime = ? WHERE id = ?",
            (utc_now(), file_mtime, row["id"]),
        )
        return False, 0

    records = build_records_for_source(source)
    indexed_at = utc_now()

    if row:
        source_id = row["id"]
        conn.execute("DELETE FROM records WHERE source_id = ?", (source_id,))
        conn.execute(
            """
            UPDATE sources
            SET repo_label = ?, repo_root = ?, owner = ?, kind = ?, intent = ?, scope = ?,
                file_hash = ?, file_mtime = ?, indexed_at = ?
            WHERE id = ?
            """,
            (
                source.repo_label,
                str(source.repo_root),
                source.owner,
                source.kind,
                source.intent,
                source.scope,
                digest,
                file_mtime,
                indexed_at,
                source_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO sources(path, repo_label, repo_root, owner, kind, intent, scope, file_hash, file_mtime, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.key,
                source.repo_label,
                str(source.repo_root),
                source.owner,
                source.kind,
                source.intent,
                source.scope,
                digest,
                file_mtime,
                indexed_at,
            ),
        )
        source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.executemany(
        """
        INSERT INTO records(
          source_id, repo_label, repo_root, owner, kind, intent, scope, title, ts, section, path,
          line_start, line_end, content, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                source_id,
                record["repo_label"],
                record["repo_root"],
                record["owner"],
                record["kind"],
                record["intent"],
                record["scope"],
                record["title"],
                record["ts"],
                record["section"],
                record["path"],
                record["line_start"],
                record["line_end"],
                record["content"],
                record["metadata_json"],
            )
            for record in records
        ],
    )
    return True, len(records)


def refresh_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("DROP TABLE IF EXISTS records_fts")
        conn.execute(
            """
            CREATE VIRTUAL TABLE records_fts USING fts5(
              title, content, owner, kind, intent, path,
              content='records',
              content_rowid='id'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO records_fts(rowid, title, content, owner, kind, intent, path)
            SELECT id, title, content, owner, kind, intent, path
            FROM records
            """
        )
    except sqlite3.OperationalError:
        pass


def refresh_branches(conn: sqlite3.Connection, repo: RepoItem) -> int:
    git_marker = repo.root / ".git"
    if not git_marker.exists():
        conn.execute("DELETE FROM branches WHERE repo_label = ?", (repo.label,))
        return 0

    try:
        current = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=repo.root,
            text=True,
            encoding="utf-8",
            errors="ignore",
        ).strip()
        raw = subprocess.check_output(
            [
                "git",
                "for-each-ref",
                "--format=%(refname:short)|%(upstream:short)|%(objectname)|%(committerdate:iso8601-strict)|%(authorname)|%(contents:subject)",
                "refs/heads",
            ],
            cwd=repo.root,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except subprocess.SubprocessError:
        return 0

    conn.execute("DELETE FROM branches WHERE repo_label = ?", (repo.label,))
    indexed_at = utc_now()
    rows = 0
    for line in raw.splitlines():
        branch_name, upstream, sha, commit_ts, author, summary = (line.split("|", 5) + ["", "", "", "", "", ""])[:6]
        conn.execute(
            """
            INSERT INTO branches(repo_label, repo_root, name, branch_name, is_current, upstream, head_sha, commit_ts, summary, author, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo.label,
                str(repo.root),
                f"{repo.label}:{branch_name}",
                branch_name,
                1 if branch_name == current else 0,
                upstream or None,
                sha or None,
                commit_ts or None,
                summary or None,
                author or None,
                indexed_at,
            ),
        )
        rows += 1
    return rows


def prune_missing_sources(conn: sqlite3.Connection, discovered: Iterable[SourceItem]) -> None:
    keep = {item.key for item in discovered}
    rows = conn.execute("SELECT id, path FROM sources").fetchall()
    for row in rows:
        if row["path"] not in keep:
            conn.execute("DELETE FROM records WHERE source_id = ?", (row["id"],))
            conn.execute("DELETE FROM sources WHERE id = ?", (row["id"],))


def build_database_once() -> dict:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)

        repos, sources = discover_sources()
        prune_missing_sources(conn, sources)

        changed_sources = 0
        inserted_records = 0
        for source in sources:
            changed, count = refresh_source(conn, source)
            if changed:
                changed_sources += 1
                inserted_records += count

        refresh_fts(conn)

        branch_count = 0
        for repo in repos:
            branch_count += refresh_branches(conn, repo)

        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('last_built_at', ?)", (utc_now(),))
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('root', ?)", (str(ROOT),))
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('repositories', ?)",
            (
                json.dumps(
                    [{"label": repo.label, "root": str(repo.root), "kind": repo.kind, "priority": repo.priority} for repo in repos],
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        owner_counts = {
            row["owner"]: row["count"]
            for row in conn.execute("SELECT owner, COUNT(*) AS count FROM records GROUP BY owner ORDER BY count DESC")
        }
        kind_counts = {
            row["kind"]: row["count"]
            for row in conn.execute("SELECT kind, COUNT(*) AS count FROM records GROUP BY kind ORDER BY count DESC")
        }
        repo_counts = {
            row["repo_label"]: row["count"]
            for row in conn.execute("SELECT repo_label, COUNT(*) AS count FROM records GROUP BY repo_label ORDER BY count DESC")
        }

        return {
            "db": str(DB_PATH),
            "builtAt": utc_now(),
            "sources": source_count,
            "changedSources": changed_sources,
            "records": record_count,
            "insertedRecords": inserted_records,
            "branches": branch_count,
            "repositories": repo_counts,
            "owners": owner_counts,
            "kinds": kind_counts,
        }
    finally:
        conn.close()


def remove_stale_database_files() -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            (Path(str(DB_PATH) + suffix)).unlink()
        except FileNotFoundError:
            pass


def build_database() -> dict:
    try:
        return build_database_once()
    except sqlite3.DatabaseError:
        remove_stale_database_files()
        return build_database_once()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the BRAIN master database.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    summary = build_database()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"BRAIN built at {summary['builtAt']}")
        print(f"Sources: {summary['sources']} | Records: {summary['records']} | Branches: {summary['branches']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
