"""
tools/search_tools.py
Codebase search using ripgrep (rg) with grep fallback.
Also includes file-finding and SQLite brain search.
"""

import subprocess
from tools.win_subprocess import run as _win_run
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("search_tools")

MAX_RESULTS = 200


def search_repo(
    query: str,
    path: str = ".",
    file_pattern: str = "",
    case_sensitive: bool = False,
    context_lines: int = 2,
) -> str:
    """
    Search codebase using ripgrep or grep fallback.
    Returns matches with file, line number, and context.
    """
    if not query.strip():
        return "ERROR: Empty search query"

    root = Path(path).resolve()
    if not root.exists():
        return f"ERROR: Path not found: {path}"

    if shutil.which("rg"):
        return _rg_search(query, str(root), file_pattern, case_sensitive, context_lines)
    else:
        return _grep_search(query, str(root), file_pattern, case_sensitive)


def _rg_search(query, path, file_pattern, case_sensitive, context_lines) -> str:
    args = [
        "rg",
        query,
        path,
        f"--context={context_lines}",
        "--line-number",
        "--color=never",
        "--heading",
        f"--max-count={MAX_RESULTS}",
    ]
    if not case_sensitive:
        args.append("--ignore-case")
    if file_pattern:
        args += ["--glob", file_pattern]

    try:
        result = _win_run(args, capture_output=True, text=True, timeout=30)
        out = result.stdout.strip()
        if not out:
            return f"No matches for '{query}' in {path}"
        lines = out.splitlines()
        if len(lines) >= MAX_RESULTS:
            out += f"\n[Results capped at {MAX_RESULTS}. Narrow your query.]"
        return out
    except subprocess.TimeoutExpired:
        return "ERROR: Search timed out"
    except Exception as e:
        return f"ERROR: {e}"


def _grep_search(query, path, file_pattern, case_sensitive) -> str:
    args = ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts"]
    if not case_sensitive:
        args.append("-i")
    args += [query, path]
    try:
        result = _win_run(args, capture_output=True, text=True, timeout=30)
        out = result.stdout.strip()
        return out if out else f"No matches for '{query}' in {path}"
    except Exception as e:
        return f"ERROR (grep): {e}"


def find_files(pattern: str, path: str = ".") -> str:
    """
    Find files matching a glob pattern.
    Example: pattern='*.py', path='src/'
    """
    root = Path(path).resolve()
    if not root.exists():
        return f"ERROR: Path not found: {path}"

    matches = list(root.rglob(pattern))
    # Filter noise
    matches = [
        m for m in matches
        if not any(part in {".git", "__pycache__", "node_modules", ".venv", "venv"}
                   for part in m.parts)
    ]

    if not matches:
        return f"No files matching '{pattern}' in {path}"

    result = [f"Found {len(matches)} file(s) matching '{pattern}':\n"]
    for m in sorted(matches)[:100]:
        result.append(f"  {m.relative_to(root)}")
    if len(matches) > 100:
        result.append(f"  ... and {len(matches) - 100} more")
    return "\n".join(result)


def grep_file(query: str, path: str, case_sensitive: bool = False) -> str:
    """Search within a single file."""
    p = Path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    q = query if case_sensitive else query.lower()

    results = []
    for i, line in enumerate(lines, 1):
        haystack = line if case_sensitive else line.lower()
        if q in haystack:
            results.append(f"{i:4d}: {line}")

    if not results:
        return f"No matches for '{query}' in {path}"
    return f"Matches in {path}:\n" + "\n".join(results[:200])


def count_lines(path: str) -> str:
    """Count lines in a file or all code files in a directory."""
    p = Path(path)
    if p.is_file():
        count = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        return f"{path}: {count:,} lines"

    if p.is_dir():
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".yaml", ".yml", ".json", ".md"}
        totals = {}
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in exts:
                if not any(part in {".git", "__pycache__", "node_modules"} for part in f.parts):
                    try:
                        count = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                        totals[f.suffix] = totals.get(f.suffix, 0) + count
                    except Exception:
                        pass
        if not totals:
            return "No code files found"
        lines = [f"{ext}: {n:,} lines" for ext, n in sorted(totals.items())]
        lines.append(f"Total: {sum(totals.values()):,} lines")
        return "\n".join(lines)

    return f"ERROR: Not found: {path}"
