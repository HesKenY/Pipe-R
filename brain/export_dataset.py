from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "brain" / "BRAIN.db"
EXPORT_DIR = ROOT / "brain" / "exports"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "brain-dataset"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name = 'records_fts'"
    ).fetchone()
    return bool(row)


def fetch_records(
    conn: sqlite3.Connection,
    query: str | None,
    repo: str | None,
    owner: str | None,
    intent: str | None,
    limit: int,
) -> list[sqlite3.Row]:
    params: list = []
    where = []
    if repo:
        where.append("r.repo_label = ?")
        params.append(repo)
    if owner:
        where.append("r.owner = ?")
        params.append(owner)
    if intent:
        where.append("r.intent = ?")
        params.append(intent)

    if query:
        if fts_available(conn):
            sql = """
            SELECT r.repo_label, r.owner, r.kind, r.intent, r.path, r.title, r.section, r.ts, r.content, r.metadata_json
            FROM records_fts
            JOIN records r ON r.id = records_fts.rowid
            WHERE records_fts MATCH ?
            """
            query_params = [query]
            if where:
                sql += " AND " + " AND ".join(where)
            sql += " ORDER BY bm25(records_fts), COALESCE(r.ts, '') DESC LIMIT ?"
            query_params.extend(params)
            query_params.append(limit)
            return conn.execute(sql, query_params).fetchall()

        like = f"%{query}%"
        sql = """
        SELECT r.repo_label, r.owner, r.kind, r.intent, r.path, r.title, r.section, r.ts, r.content, r.metadata_json
        FROM records r
        WHERE (r.title LIKE ? OR r.content LIKE ?)
        """
        query_params = [like, like]
        if where:
            sql += " AND " + " AND ".join(where)
        sql += " ORDER BY COALESCE(r.ts, '') DESC LIMIT ?"
        query_params.extend(params)
        query_params.append(limit)
        return conn.execute(sql, query_params).fetchall()

    sql = """
    SELECT r.repo_label, r.owner, r.kind, r.intent, r.path, r.title, r.section, r.ts, r.content, r.metadata_json
    FROM records r
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(r.ts, '') DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def fetch_branches(
    conn: sqlite3.Connection,
    query: str | None,
    repo: str | None,
    limit: int,
) -> list[sqlite3.Row]:
    sql = """
    SELECT repo_label, branch_name, upstream, head_sha, commit_ts, summary, author, is_current
    FROM branches
    WHERE 1=1
    """
    params: list = []
    if repo:
        sql += " AND repo_label = ?"
        params.append(repo)
    if query:
        like = f"%{query}%"
        sql += """
        AND (
          branch_name LIKE ?
          OR COALESCE(summary, '') LIKE ?
          OR COALESCE(author, '') LIKE ?
          OR COALESCE(upstream, '') LIKE ?
          OR COALESCE(head_sha, '') LIKE ?
        )
        """
        params.extend([like, like, like, like, like])
    sql += " ORDER BY COALESCE(commit_ts, '') DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def export_dataset(
    name: str,
    query: str | None,
    repo: str | None,
    owner: str | None,
    intent: str | None,
    limit: int,
) -> dict:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"BRAIN database not found at {DB_PATH}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        records = fetch_records(conn, query, repo, owner, intent, limit)
        branch_limit = max(4, min(40, max(1, limit // 8)))
        branches = fetch_branches(conn, query, repo, branch_limit)
    finally:
        conn.close()

    stamp = utc_now().replace(":", "-")
    slug = slugify(name)
    dataset_path = EXPORT_DIR / f"{stamp}-{slug}.jsonl"
    manifest_path = EXPORT_DIR / f"{stamp}-{slug}.manifest.json"

    repo_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    total_items = 0

    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in records:
            item = {
                "source": "record",
                "repo": row["repo_label"],
                "owner": row["owner"],
                "kind": row["kind"],
                "intent": row["intent"],
                "path": row["path"],
                "title": row["title"],
                "section": row["section"],
                "timestamp": row["ts"],
                "text": row["content"],
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else None,
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            repo_counts[row["repo_label"]] += 1
            kind_counts[row["kind"]] += 1
            total_items += 1

        for row in branches:
            text = (
                f"Repository {row['repo_label']} branch {row['branch_name']} "
                f"(current={bool(row['is_current'])}) "
                f"summary={row['summary'] or ''} "
                f"author={row['author'] or ''} "
                f"upstream={row['upstream'] or ''} "
                f"sha={row['head_sha'] or ''}"
            ).strip()
            item = {
                "source": "branch",
                "repo": row["repo_label"],
                "owner": "shared",
                "kind": "branch_snapshot",
                "intent": "branching",
                "path": f"{row['repo_label']}/.git/{row['branch_name']}",
                "title": f"{row['repo_label']} | {row['branch_name']}",
                "section": "branch",
                "timestamp": row["commit_ts"],
                "text": text,
                "metadata": {
                    "branch_name": row["branch_name"],
                    "upstream": row["upstream"],
                    "head_sha": row["head_sha"],
                    "author": row["author"],
                    "summary": row["summary"],
                    "is_current": bool(row["is_current"]),
                },
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            repo_counts[row["repo_label"]] += 1
            kind_counts["branch_snapshot"] += 1
            total_items += 1

    manifest = {
        "name": name,
        "generatedAt": utc_now(),
        "datasetFile": str(dataset_path),
        "datasetFileRelative": str(dataset_path.relative_to(ROOT)),
        "filters": {
            "query": query,
            "repo": repo,
            "owner": owner,
            "intent": intent,
            "limit": limit,
        },
        "recordCount": len(records),
        "branchCount": len(branches),
        "itemCount": total_items,
        "repositories": dict(repo_counts),
        "kinds": dict(kind_counts),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifestFile"] = str(manifest_path)
    manifest["manifestFileRelative"] = str(manifest_path.relative_to(ROOT))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a BRAIN dataset slice for training/spec work.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--query")
    parser.add_argument("--repo")
    parser.add_argument("--owner")
    parser.add_argument("--intent")
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--json", action="store_true", help="Emit summary as JSON")
    args = parser.parse_args()

    summary = export_dataset(
        name=args.name,
        query=args.query,
        repo=args.repo,
        owner=args.owner,
        intent=args.intent,
        limit=max(1, min(5000, args.limit)),
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Exported {summary['itemCount']} items to {summary['datasetFileRelative']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
