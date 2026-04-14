"""
tools/filesystem_tools.py
File read, write, patch, and tree listing.
All writes go through PatchEngine for backup safety.
"""

import os
from pathlib import Path
from typing import Optional
import logging

from agent_core.patch_engine import PatchEngine

logger = logging.getLogger("fs_tools")
_patch_engine = PatchEngine()


def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    p = Path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"
    if not p.is_file():
        return f"ERROR: Not a file: {path}"
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories as needed. Backs up existing."""
    ok, msg = _patch_engine.write_file(path, content)
    return msg


def apply_patch(path: str, diff: str) -> str:
    """Apply a unified diff to a file."""
    ok, msg = _patch_engine.apply_patch(path, diff)
    return msg


def list_tree(path: str = ".", depth: int = 3) -> str:
    """Return a tree view of a directory."""
    root = Path(path)
    if not root.exists():
        return f"ERROR: Path not found: {path}"

    lines = [str(root)]
    _build_tree(root, lines, prefix="", current_depth=0, max_depth=depth)
    return "\n".join(lines)


def _build_tree(path: Path, lines: list, prefix: str, current_depth: int, max_depth: int):
    if current_depth >= max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    except PermissionError:
        return

    # Filter out common noise
    entries = [e for e in entries if e.name not in {
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".mypy_cache", "dist", "build", ".pytest_cache"
    }]

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            _build_tree(entry, lines, prefix + extension, current_depth + 1, max_depth)


def delete_file(path: str) -> str:
    """Delete a file (backs up first)."""
    p = Path(path)
    if not p.exists():
        return f"ERROR: File not found: {path}"
    content = p.read_text(encoding="utf-8", errors="replace")
    _patch_engine._backup(p, content)
    p.unlink()
    return f"Deleted: {path} (backup created)"


def file_info(path: str) -> str:
    """Return metadata about a file."""
    p = Path(path)
    if not p.exists():
        return f"ERROR: Not found: {path}"
    stat = p.stat()
    return (
        f"Path: {p.resolve()}\n"
        f"Size: {stat.st_size:,} bytes\n"
        f"Modified: {stat.st_mtime}\n"
        f"Is file: {p.is_file()}\n"
        f"Is dir: {p.is_dir()}\n"
    )
