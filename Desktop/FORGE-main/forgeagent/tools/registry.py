"""All 12 built-in tools."""
from __future__ import annotations
import os
import re
import json
import subprocess
import glob as globmod
from pathlib import Path
from datetime import datetime
from typing import Any
from ..core.interfaces import Tool, ToolDefinition, ToolContext, ToolRegistry


class BashTool(Tool):
    definition = ToolDefinition("bash", "Execute a shell command. Returns stdout/stderr.", {
        "type": "object",
        "properties": {"command": {"type": "string"}, "timeout": {"type": "number"}},
        "required": ["command"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        cmd = str(inp.get("command", ""))
        timeout = int(inp.get("timeout", 30))
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=ctx.cwd)
            return f"Exit {r.returncode}\n{r.stdout[:6000]}" + (f"\nSTDERR: {r.stderr[:3000]}" if r.stderr else "")
        except subprocess.TimeoutExpired:
            return "Error: command timed out"
        except Exception as e:
            return f"Error: {e}"


class ReadFileTool(Tool):
    definition = ToolDefinition("read_file", "Read a file with line numbers.", {
        "type": "object",
        "properties": {"path": {"type": "string"}, "start_line": {"type": "number"}, "end_line": {"type": "number"}},
        "required": ["path"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        fp = Path(ctx.cwd) / str(inp.get("path", ""))
        if not fp.exists():
            return f"Error: File not found: {fp}"
        text = fp.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        start = max(0, int(inp.get("start_line", 1)) - 1)
        end = int(inp.get("end_line", len(lines)))
        numbered = "\n".join(f"{start + i + 1}\t{l}" for i, l in enumerate(lines[start:end]))
        return f"{fp} ({len(lines)} lines)\n{numbered[:8000]}"


class WriteFileTool(Tool):
    definition = ToolDefinition("write_file", "Write content to a file, creating dirs as needed.", {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        fp = Path(ctx.cwd) / str(inp.get("path", ""))
        content = str(inp.get("content", ""))
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return f"Wrote {fp} ({len(content)} bytes)"


class EditFileTool(Tool):
    definition = ToolDefinition("edit_file", "Find-and-replace in a file. old_text must match exactly once.", {
        "type": "object",
        "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
        "required": ["path", "old_text", "new_text"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        fp = Path(ctx.cwd) / str(inp.get("path", ""))
        if not fp.exists():
            return f"Error: File not found: {fp}"
        content = fp.read_text(encoding="utf-8")
        old = str(inp.get("old_text", ""))
        new = str(inp.get("new_text", ""))
        count = content.count(old)
        if count == 0:
            return "Error: old_text not found in file"
        if count > 1:
            return f"Error: old_text found {count} times — must be unique"
        fp.write_text(content.replace(old, new, 1, encoding="utf-8"), encoding="utf-8")
        return f"Edited {fp} (1 replacement)"


class ListDirTool(Tool):
    definition = ToolDefinition("list_dir", "List files and directories.", {
        "type": "object",
        "properties": {"path": {"type": "string"}, "recursive": {"type": "boolean"}},
        "required": ["path"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        dp = Path(ctx.cwd) / str(inp.get("path", "."))
        if not dp.exists():
            return f"Error: Directory not found: {dp}"
        recursive = bool(inp.get("recursive", False))
        entries = []

        def walk(d: Path, depth: int):
            if depth > (2 if recursive else 0):
                return
            try:
                for e in sorted(d.iterdir()):
                    if e.name.startswith(".") or e.name == "node_modules":
                        continue
                    rel = e.relative_to(dp)
                    icon = "D" if e.is_dir() else "F"
                    size = f" ({e.stat().st_size}B)" if e.is_file() else ""
                    entries.append(f"{icon} {rel}{size}")
                    if e.is_dir():
                        walk(e, depth + 1)
            except PermissionError:
                pass

        walk(dp, 0)
        return "\n".join(entries) if entries else "(empty directory)"


class SearchFilesTool(Tool):
    definition = ToolDefinition("search_files", "Search for text across files (grep).", {
        "type": "object",
        "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "glob": {"type": "string"}},
        "required": ["pattern", "path"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        pattern = str(inp.get("pattern", ""))
        dp = Path(ctx.cwd) / str(inp.get("path", "."))
        file_glob = str(inp.get("glob", ""))
        results = []
        try:
            for fp in dp.rglob(file_glob or "*"):
                if fp.is_file() and not any(p.startswith(".") or p == "node_modules" for p in fp.parts):
                    try:
                        for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                            if pattern.lower() in line.lower():
                                results.append(f"{fp}:{i}: {line.strip()}")
                                if len(results) >= 30:
                                    return "\n".join(results)
                    except Exception:
                        pass
        except Exception:
            pass
        return "\n".join(results) if results else "No matches found."


class GlobTool(Tool):
    definition = ToolDefinition("glob", "Find files matching a glob pattern.", {
        "type": "object",
        "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
        "required": ["pattern"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        pattern = str(inp.get("pattern", ""))
        dp = Path(ctx.cwd) / str(inp.get("path", "."))
        files = list(dp.rglob(pattern))[:50]
        if files:
            return f"Found {len(files)} files:\n" + "\n".join(str(f) for f in files)
        return "No files matched."


class WebFetchTool(Tool):
    definition = ToolDefinition("web_fetch", "Fetch URL contents (truncated to 8000 chars).", {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        import httpx
        url = str(inp.get("url", ""))
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers={"User-Agent": "ForgeAgent/3.0"})
                if resp.status_code >= 400:
                    return f"HTTP {resp.status_code}: {resp.reason_phrase}"
                return resp.text[:8000]
        except Exception as e:
            return f"Fetch error: {e}"


class DateTimeTool(Tool):
    definition = ToolDefinition("datetime", "Returns current local date and time.", {"type": "object", "properties": {}})

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        return str(datetime.now())


class TaskTool(Tool):
    definition = ToolDefinition("task", "Manage a task/todo list. Actions: list, add, done, remove.", {
        "type": "object",
        "properties": {"action": {"type": "string"}, "text": {"type": "string"}},
        "required": ["action"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        task_file = Path(ctx.memory_dir) / "tasks.json"
        tasks: list[dict] = []
        if task_file.exists():
            tasks = json.loads(task_file.read_text())

        action = str(inp.get("action", "list"))
        if action == "add":
            tid = max((t["id"] for t in tasks), default=0) + 1
            tasks.append({"id": tid, "text": str(inp.get("text", "")), "done": False, "created": datetime.now().isoformat()})
            task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
            return f"Task #{tid} added."
        elif action == "done":
            num = int(inp.get("text", 0))
            task = next((t for t in tasks if t["id"] == num), None)
            if not task:
                return f"Task #{num} not found."
            task["done"] = True
            task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
            return f"Task #{num} marked done."
        elif action == "remove":
            num = int(inp.get("text", 0))
            tasks = [t for t in tasks if t["id"] != num]
            task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
            return f"Task #{num} removed."
        else:
            if not tasks:
                return "No tasks."
            return "\n".join(f"{'V' if t['done'] else 'O'} #{t['id']}: {t['text']}" for t in tasks)


class MemorySaveTool(Tool):
    definition = ToolDefinition("memory_save", "Save information to long-term memory.", {
        "type": "object",
        "properties": {"section": {"type": "string"}, "content": {"type": "string"}},
        "required": ["section", "content"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        mem_dir = Path(ctx.memory_dir)
        mem_dir.mkdir(parents=True, exist_ok=True)
        mem_file = mem_dir / "MEMORY.md"
        if not mem_file.exists():
            mem_file.write_text("# ForgeAgent Memory\n\n", encoding="utf-8")
        entry = f"\n## {inp.get('section')} — {datetime.now().isoformat()}\n{inp.get('content')}\n"
        with open(mem_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return f'Saved to memory under "{inp.get("section")}"'


class MemorySearchTool(Tool):
    definition = ToolDefinition("memory_search", "Search long-term memory.", {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    })

    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str:
        mem_file = Path(ctx.memory_dir) / "MEMORY.md"
        if not mem_file.exists():
            return "Memory is empty."
        content = mem_file.read_text(encoding="utf-8")
        q = str(inp.get("query", "")).lower()
        matches = [l for l in content.split("\n") if q in l.lower()]
        return "\n".join(matches[:20]) if matches else f'No matches for "{inp.get("query")}"'


def create_tool_registry() -> ToolRegistry:
    tools: list[Tool] = [
        BashTool(), ReadFileTool(), WriteFileTool(), EditFileTool(),
        ListDirTool(), SearchFilesTool(), GlobTool(), WebFetchTool(),
        DateTimeTool(), TaskTool(), MemorySaveTool(), MemorySearchTool(),
    ]
    return {t.definition.name: t for t in tools}
