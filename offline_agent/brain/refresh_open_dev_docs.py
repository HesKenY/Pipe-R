"""
refresh_open_dev_docs.py

Pull a curated set of open-licensed coding docs from official upstream
repos, store raw mirrors locally, chunk them into brain_index/*.md, and
rebuild the local memory index.

This keeps KenAI's brain fed with real coding references without reaching
into the desktop Claude clone or relying on random web scrape junk.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
BRAIN_INDEX = HERE / "brain_index"
WEB_ROOT = HERE / "web_sources" / "open_dev_docs"
RAW_ROOT = WEB_ROOT / "raw"
MANIFEST_PATH = WEB_ROOT / "generated_manifest.json"
INDEX_FILE = BRAIN_INDEX / "ext_open_dev_sources.md"
CHUNK_PREFIX = "ext_"
MAX_CHARS = 14000
OVERLAP_CHARS = 500

sys.path.insert(0, str(PROJECT_ROOT))


SOURCES = [
    {
        "provider": "python",
        "slug": "argparse",
        "title": "Python argparse",
        "repo_url": "https://github.com/python/cpython",
        "doc_url": "https://github.com/python/cpython/blob/main/Doc/library/argparse.rst",
        "raw_url": "https://raw.githubusercontent.com/python/cpython/main/Doc/library/argparse.rst",
        "license_name": "PSF License Version 2",
        "license_url": "https://github.com/python/cpython/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/python/cpython/main/LICENSE",
    },
    {
        "provider": "python",
        "slug": "json",
        "title": "Python json",
        "repo_url": "https://github.com/python/cpython",
        "doc_url": "https://github.com/python/cpython/blob/main/Doc/library/json.rst",
        "raw_url": "https://raw.githubusercontent.com/python/cpython/main/Doc/library/json.rst",
        "license_name": "PSF License Version 2",
        "license_url": "https://github.com/python/cpython/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/python/cpython/main/LICENSE",
    },
    {
        "provider": "python",
        "slug": "pathlib",
        "title": "Python pathlib",
        "repo_url": "https://github.com/python/cpython",
        "doc_url": "https://github.com/python/cpython/blob/main/Doc/library/pathlib.rst",
        "raw_url": "https://raw.githubusercontent.com/python/cpython/main/Doc/library/pathlib.rst",
        "license_name": "PSF License Version 2",
        "license_url": "https://github.com/python/cpython/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/python/cpython/main/LICENSE",
    },
    {
        "provider": "python",
        "slug": "sqlite3",
        "title": "Python sqlite3",
        "repo_url": "https://github.com/python/cpython",
        "doc_url": "https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst",
        "raw_url": "https://raw.githubusercontent.com/python/cpython/main/Doc/library/sqlite3.rst",
        "license_name": "PSF License Version 2",
        "license_url": "https://github.com/python/cpython/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/python/cpython/main/LICENSE",
    },
    {
        "provider": "python",
        "slug": "subprocess",
        "title": "Python subprocess",
        "repo_url": "https://github.com/python/cpython",
        "doc_url": "https://github.com/python/cpython/blob/main/Doc/library/subprocess.rst",
        "raw_url": "https://raw.githubusercontent.com/python/cpython/main/Doc/library/subprocess.rst",
        "license_name": "PSF License Version 2",
        "license_url": "https://github.com/python/cpython/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/python/cpython/main/LICENSE",
    },
    {
        "provider": "fastapi",
        "slug": "path_params",
        "title": "FastAPI path params",
        "repo_url": "https://github.com/fastapi/fastapi",
        "doc_url": "https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/path-params.md",
        "raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/tutorial/path-params.md",
        "license_name": "MIT",
        "license_url": "https://github.com/fastapi/fastapi/blob/master/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE",
    },
    {
        "provider": "fastapi",
        "slug": "query_params",
        "title": "FastAPI query params",
        "repo_url": "https://github.com/fastapi/fastapi",
        "doc_url": "https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/query-params.md",
        "raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/tutorial/query-params.md",
        "license_name": "MIT",
        "license_url": "https://github.com/fastapi/fastapi/blob/master/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE",
    },
    {
        "provider": "fastapi",
        "slug": "body",
        "title": "FastAPI request body",
        "repo_url": "https://github.com/fastapi/fastapi",
        "doc_url": "https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/body.md",
        "raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/tutorial/body.md",
        "license_name": "MIT",
        "license_url": "https://github.com/fastapi/fastapi/blob/master/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE",
    },
    {
        "provider": "fastapi",
        "slug": "testing",
        "title": "FastAPI testing",
        "repo_url": "https://github.com/fastapi/fastapi",
        "doc_url": "https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/testing.md",
        "raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/tutorial/testing.md",
        "license_name": "MIT",
        "license_url": "https://github.com/fastapi/fastapi/blob/master/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE",
    },
    {
        "provider": "fastapi",
        "slug": "dependencies",
        "title": "FastAPI dependencies in path operation decorators",
        "repo_url": "https://github.com/fastapi/fastapi",
        "doc_url": "https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/dependencies/dependencies-in-path-operation-decorators.md",
        "raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/tutorial/dependencies/dependencies-in-path-operation-decorators.md",
        "license_name": "MIT",
        "license_url": "https://github.com/fastapi/fastapi/blob/master/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE",
    },
    {
        "provider": "pydantic_ai",
        "slug": "agent",
        "title": "Pydantic AI agent",
        "repo_url": "https://github.com/pydantic/pydantic-ai",
        "doc_url": "https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md",
        "raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/agent.md",
        "license_name": "MIT",
        "license_url": "https://github.com/pydantic/pydantic-ai/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/LICENSE",
    },
    {
        "provider": "pydantic_ai",
        "slug": "tools",
        "title": "Pydantic AI tools",
        "repo_url": "https://github.com/pydantic/pydantic-ai",
        "doc_url": "https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md",
        "raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/tools.md",
        "license_name": "MIT",
        "license_url": "https://github.com/pydantic/pydantic-ai/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/LICENSE",
    },
    {
        "provider": "pydantic_ai",
        "slug": "testing",
        "title": "Pydantic AI testing",
        "repo_url": "https://github.com/pydantic/pydantic-ai",
        "doc_url": "https://github.com/pydantic/pydantic-ai/blob/main/docs/testing.md",
        "raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/testing.md",
        "license_name": "MIT",
        "license_url": "https://github.com/pydantic/pydantic-ai/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/LICENSE",
    },
    {
        "provider": "pydantic_ai",
        "slug": "message_history",
        "title": "Pydantic AI message history",
        "repo_url": "https://github.com/pydantic/pydantic-ai",
        "doc_url": "https://github.com/pydantic/pydantic-ai/blob/main/docs/message-history.md",
        "raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/message-history.md",
        "license_name": "MIT",
        "license_url": "https://github.com/pydantic/pydantic-ai/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/LICENSE",
    },
    {
        "provider": "pydantic_ai",
        "slug": "multi_agent",
        "title": "Pydantic AI multi-agent applications",
        "repo_url": "https://github.com/pydantic/pydantic-ai",
        "doc_url": "https://github.com/pydantic/pydantic-ai/blob/main/docs/multi-agent-applications.md",
        "raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/docs/multi-agent-applications.md",
        "license_name": "MIT",
        "license_url": "https://github.com/pydantic/pydantic-ai/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/pydantic/pydantic-ai/main/LICENSE",
    },
    {
        "provider": "node",
        "slug": "path",
        "title": "Node.js path",
        "repo_url": "https://github.com/nodejs/node",
        "doc_url": "https://github.com/nodejs/node/blob/main/doc/api/path.md",
        "raw_url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/path.md",
        "license_name": "MIT-like Node.js license",
        "license_url": "https://github.com/nodejs/node/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/nodejs/node/main/LICENSE",
    },
    {
        "provider": "node",
        "slug": "child_process",
        "title": "Node.js child_process",
        "repo_url": "https://github.com/nodejs/node",
        "doc_url": "https://github.com/nodejs/node/blob/main/doc/api/child_process.md",
        "raw_url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/child_process.md",
        "license_name": "MIT-like Node.js license",
        "license_url": "https://github.com/nodejs/node/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/nodejs/node/main/LICENSE",
    },
    {
        "provider": "node",
        "slug": "fs",
        "title": "Node.js fs",
        "repo_url": "https://github.com/nodejs/node",
        "doc_url": "https://github.com/nodejs/node/blob/main/doc/api/fs.md",
        "raw_url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/fs.md",
        "license_name": "MIT-like Node.js license",
        "license_url": "https://github.com/nodejs/node/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/nodejs/node/main/LICENSE",
    },
    {
        "provider": "node",
        "slug": "http",
        "title": "Node.js http",
        "repo_url": "https://github.com/nodejs/node",
        "doc_url": "https://github.com/nodejs/node/blob/main/doc/api/http.md",
        "raw_url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/http.md",
        "license_name": "MIT-like Node.js license",
        "license_url": "https://github.com/nodejs/node/blob/main/LICENSE",
        "license_raw_url": "https://raw.githubusercontent.com/nodejs/node/main/LICENSE",
    },
]


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "KenAI-open-dev-docs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read()
    return body.decode("utf-8", errors="ignore")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", "    ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap_chars: int = OVERLAP_CHARS) -> list[str]:
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if not blocks:
        return []

    chunks: list[str] = []
    current = ""

    def push_chunk(value: str) -> None:
        cleaned = value.strip()
        if cleaned:
            chunks.append(cleaned + "\n")

    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            push_chunk(current)
            tail = current[-overlap_chars:].strip()
            current = f"{tail}\n\n{block}" if tail else block
            if len(current) <= max_chars:
                continue

        lines = block.splitlines()
        current = ""
        for line in lines:
            piece = line if not current else f"{current}\n{line}"
            if len(piece) <= max_chars:
                current = piece
                continue
            push_chunk(current)
            tail = current[-overlap_chars:].strip()
            current = f"{tail}\n{line}" if tail else line

    if current:
        push_chunk(current)

    return chunks


def clean_previous_outputs() -> list[str]:
    deleted: list[str] = []
    if not MANIFEST_PATH.exists():
        return deleted
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return deleted

    for rel in manifest.get("brain_files", []):
        path = BRAIN_INDEX / rel
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    return deleted


def write_license_files(sources: list[dict]) -> dict[str, str]:
    written: dict[str, str] = {}
    seen: set[str] = set()
    for src in sources:
        provider = src["provider"]
        if provider in seen:
            continue
        seen.add(provider)
        license_text = normalize_text(fetch_text(src["license_raw_url"]))
        provider_dir = RAW_ROOT / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        out = provider_dir / "LICENSE.txt"
        out.write_text(license_text, encoding="utf-8")
        written[provider] = str(out)
    return written


def main() -> int:
    BRAIN_INDEX.mkdir(parents=True, exist_ok=True)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    WEB_ROOT.mkdir(parents=True, exist_ok=True)

    deleted = clean_previous_outputs()
    if deleted:
        print(f"removed {len(deleted)} previous generated brain files")

    generated_files: list[str] = []
    index_rows: list[str] = []
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    license_files = write_license_files(SOURCES)

    for src in SOURCES:
        provider = src["provider"]
        slug = src["slug"]
        title = src["title"]

        raw_text = normalize_text(fetch_text(src["raw_url"]))

        ext = Path(src["raw_url"]).suffix or ".txt"
        raw_dir = RAW_ROOT / provider
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{slug}{ext}"
        raw_path.write_text(raw_text, encoding="utf-8")

        chunks = chunk_text(raw_text)
        if not chunks:
            continue

        index_rows.append(
            "\n".join(
                [
                    f"## {title}",
                    f"- provider: {provider}",
                    f"- source: {src['doc_url']}",
                    f"- repo: {src['repo_url']}",
                    f"- license: {src['license_name']} ({src['license_url']})",
                    f"- raw mirror: brain/web_sources/open_dev_docs/raw/{provider}/{raw_path.name}",
                    f"- chunk count: {len(chunks)}",
                ]
            )
        )

        for idx, chunk in enumerate(chunks, start=1):
            filename = f"{CHUNK_PREFIX}{provider}_{slug}_{idx:02d}.md"
            out_path = BRAIN_INDEX / filename
            header = "\n".join(
                [
                    f"# {title} ({idx}/{len(chunks)})",
                    f"source: {src['doc_url']}",
                    f"repo: {src['repo_url']}",
                    f"license: {src['license_name']} | {src['license_url']}",
                    f"fetched_at: {fetched_at}",
                    "",
                ]
            )
            out_path.write_text(header + chunk, encoding="utf-8")
            generated_files.append(filename)

    index_lines = [
        "# external open dev sources",
        "",
        "official coding docs mirrored into this brain from open-licensed upstream repos.",
        f"fetched_at: {fetched_at}",
        "",
        "## providers",
        "",
    ]
    for provider, license_path in sorted(license_files.items()):
        rel = Path(license_path).relative_to(HERE).as_posix()
        index_lines.append(f"- {provider}: {rel}")
    index_lines.extend(["", *index_rows, ""])
    INDEX_FILE.write_text("\n".join(index_lines), encoding="utf-8")
    generated_files.append(INDEX_FILE.name)

    manifest = {
        "generated_at": fetched_at,
        "brain_files": sorted(generated_files),
        "source_count": len(SOURCES),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    from agent_core.memory_retriever import MemoryRetriever

    retriever = MemoryRetriever()
    stats = retriever.stats()
    print(
        json.dumps(
            {
                "generated_at": fetched_at,
                "source_count": len(SOURCES),
                "brain_files_written": len(generated_files),
                "index_stats": stats,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
