from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "brain" / "BRAIN.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def meta_value(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name = 'records_fts'"
    ).fetchone()
    return bool(row)


def status(conn: sqlite3.Connection) -> dict:
    return {
        "db": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "lastBuiltAt": meta_value(conn, "last_built_at"),
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "records": conn.execute("SELECT COUNT(*) FROM records").fetchone()[0],
        "branches": conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0],
        "repositories": {
            row["repo_label"]: row["count"]
            for row in conn.execute("SELECT repo_label, COUNT(*) AS count FROM records GROUP BY repo_label ORDER BY count DESC")
        },
        "branchRepositories": {
            row["repo_label"]: row["count"]
            for row in conn.execute("SELECT repo_label, COUNT(*) AS count FROM branches GROUP BY repo_label ORDER BY count DESC")
        },
        "owners": {
            row["owner"]: row["count"]
            for row in conn.execute("SELECT owner, COUNT(*) AS count FROM records GROUP BY owner ORDER BY count DESC")
        },
        "kinds": {
            row["kind"]: row["count"]
            for row in conn.execute("SELECT kind, COUNT(*) AS count FROM records GROUP BY kind ORDER BY count DESC")
        },
    }


def search_records(
    conn: sqlite3.Connection,
    query: str,
    repo: str | None,
    owner: str | None,
    intent: str | None,
    limit: int,
) -> list[dict]:
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

    if fts_available(conn):
        sql = """
        SELECT r.id, r.repo_label, r.owner, r.kind, r.intent, r.title, r.ts, r.path, r.section,
               snippet(records_fts, 1, '[', ']', ' ... ', 18) AS preview,
               bm25(records_fts) AS score
        FROM records_fts
        JOIN records r ON r.id = records_fts.rowid
        WHERE records_fts MATCH ?
        """
        search_params = [query]
        if where:
            sql += " AND " + " AND ".join(where)
        sql += " ORDER BY score, COALESCE(r.ts, '') DESC LIMIT ?"
        search_params.extend(params)
        search_params.append(limit)
        rows = conn.execute(sql, search_params).fetchall()
    else:
        sql = """
        SELECT r.id, r.repo_label, r.owner, r.kind, r.intent, r.title, r.ts, r.path, r.section,
               substr(r.content, 1, 220) AS preview,
               9999 AS score
        FROM records r
        WHERE (r.title LIKE ? OR r.content LIKE ?)
        """
        like = f"%{query}%"
        search_params = [like, like]
        if where:
            sql += " AND " + " AND ".join(where)
        sql += " ORDER BY COALESCE(r.ts, '') DESC LIMIT ?"
        search_params.extend(params)
        search_params.append(limit)
        rows = conn.execute(sql, search_params).fetchall()

    return [dict(row) | {"source": "records"} for row in rows]


def search_branches(
    conn: sqlite3.Connection,
    query: str,
    repo: str | None,
    limit: int,
) -> list[dict]:
    like = f"%{query}%"
    sql = """
    SELECT id, repo_label, branch_name, is_current, upstream, head_sha, commit_ts, summary, author
    FROM branches
    WHERE (
      branch_name LIKE ?
      OR COALESCE(summary, '') LIKE ?
      OR COALESCE(author, '') LIKE ?
      OR COALESCE(upstream, '') LIKE ?
      OR COALESCE(head_sha, '') LIKE ?
    )
    """
    params: list = [like, like, like, like, like]
    if repo:
        sql += " AND repo_label = ?"
        params.append(repo)
    sql += " ORDER BY COALESCE(commit_ts, '') DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        preview_parts = []
        if row["summary"]:
            preview_parts.append(row["summary"])
        if row["head_sha"]:
            preview_parts.append(f"sha {row['head_sha'][:8]}")
        if row["upstream"]:
            preview_parts.append(f"upstream {row['upstream']}")
        results.append(
            {
                "id": f"branch:{row['id']}",
                "repo_label": row["repo_label"],
                "owner": "shared",
                "kind": "branch_snapshot",
                "intent": "branching",
                "title": f"{row['repo_label']} | {row['branch_name']}",
                "ts": row["commit_ts"],
                "path": f"{row['repo_label']}/.git/{row['branch_name']}",
                "section": "branch",
                "preview": " | ".join(preview_parts) or row["branch_name"],
                "score": 9998,
                "source": "branches",
            }
        )
    return results


def search(
    conn: sqlite3.Connection,
    query: str,
    repo: str | None,
    owner: str | None,
    intent: str | None,
    limit: int,
) -> list[dict]:
    record_results = search_records(conn, query, repo, owner, intent, max(limit, 10))
    branch_results = search_branches(conn, query, repo, max(4, limit // 2))

    combined = record_results + branch_results
    combined.sort(key=lambda row: (row.get("ts") or "", -float(row.get("score") or 9999)), reverse=True)
    trimmed = combined[:limit]
    for row in trimmed:
        row.pop("score", None)
    return trimmed


def build_context_pack(
    conn: sqlite3.Connection,
    query: str,
    repo: str | None,
    owner: str | None,
    intent: str | None,
    limit: int,
    target: str,
) -> dict:
    results = search(conn, query, repo, owner, intent, limit)
    grouped = []
    for row in results:
        grouped.append(
            {
                "title": row["title"],
                "repo": row["repo_label"],
                "owner": row["owner"],
                "kind": row["kind"],
                "intent": row["intent"],
                "path": row["path"],
                "ts": row["ts"],
                "preview": row["preview"],
                "source": row.get("source", "records"),
            }
        )

    return {
        "query": query,
        "target": target,
        "repoFilter": repo,
        "ownerFilter": owner,
        "intentFilter": intent,
        "count": len(grouped),
        "results": grouped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the BRAIN master database.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--repo")
    search_parser.add_argument("--owner")
    search_parser.add_argument("--intent")
    search_parser.add_argument("--limit", type=int, default=8)

    context_parser = sub.add_parser("context")
    context_parser.add_argument("query")
    context_parser.add_argument("--repo")
    context_parser.add_argument("--owner")
    context_parser.add_argument("--intent")
    context_parser.add_argument("--limit", type=int, default=10)
    context_parser.add_argument("--target", choices=("local", "cloud"), default="local")

    args = parser.parse_args()
    conn = connect()
    try:
        if args.cmd == "status":
            print(json.dumps(status(conn), indent=2))
        elif args.cmd == "search":
            print(json.dumps(search(conn, args.query, args.repo, args.owner, args.intent, args.limit), indent=2))
        elif args.cmd == "context":
            print(
                json.dumps(
                    build_context_pack(conn, args.query, args.repo, args.owner, args.intent, args.limit, args.target),
                    indent=2,
                )
            )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
