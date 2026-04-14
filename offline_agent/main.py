"""
main.py
Ken AI offline — local coding agent server.
Serves the UI at http://localhost:7778
WebSocket at ws://localhost:7778/ws

Port 7778 (not 7777) — Pipe-R's Node server already owns 7777.
Running them side by side is expected.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Agent core
from agent_core.permissions import PermissionsEngine
from agent_core.memory_retriever import MemoryRetriever
from agent_core.session_manager import SessionManager
from agent_core.tool_router import ToolRouter
from agent_core.planner import Planner

# Tools
from tools import filesystem_tools as fs
from tools import git_tools as git
from tools import shell_tools as shell
from tools import search_tools as search
from tools import ui_tools as ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("main")

# ─── Bootstrap ───────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

app = FastAPI(title="Ken AI offline", version="0.1.0-skeleton")

# Global singletons
permissions = PermissionsEngine(initial_mode=0)
memory = MemoryRetriever()
session = SessionManager()
router = ToolRouter(permissions, session)

# Active WebSocket connections
connections: list[WebSocket] = []

# Active planner task
current_task: Optional[asyncio.Task] = None
planner: Optional[Planner] = None


# ─── Tool Registration ────────────────────────────────────────────────────────

def register_tools():
    # Filesystem — Mode 0+
    router.register("read_file",  fs.read_file,   min_mode=0, description="Read a file's contents")
    router.register("list_tree",  fs.list_tree,   min_mode=0, description="List directory tree")
    router.register("file_info",  fs.file_info,   min_mode=0, description="File metadata")
    router.register("write_file", fs.write_file,  min_mode=1, description="Write/overwrite a file")
    router.register("apply_patch",fs.apply_patch, min_mode=1, description="Apply unified diff patch")
    router.register("delete_file",fs.delete_file, min_mode=2, description="Delete a file")

    # Search — Mode 0+
    router.register("search_repo",  search.search_repo,  min_mode=0, description="Search codebase (ripgrep)")
    router.register("find_files",   search.find_files,   min_mode=0, description="Find files by glob pattern")
    router.register("grep_file",    search.grep_file,    min_mode=0, description="Search within a single file")
    router.register("count_lines",  search.count_lines,  min_mode=0, description="Count lines of code")

    # Git — Mode 0+
    router.register("git_status",  git.git_status,  min_mode=0, description="git status")
    router.register("git_diff",    git.git_diff,    min_mode=0, description="git diff")
    router.register("git_log",     git.git_log,     min_mode=0, description="git log")
    router.register("git_add",     git.git_add,     min_mode=1, description="git add")
    router.register("git_commit",  git.git_commit,  min_mode=1, description="git commit")
    router.register("git_branch",  git.git_branch,  min_mode=1, description="git branch/checkout")
    router.register("git_stash",   git.git_stash,   min_mode=1, description="git stash")

    # Shell — Mode 1+
    router.register("run_command",    shell.run_command,    min_mode=1, description="Run shell command")
    router.register("run_tests",      shell.run_tests,      min_mode=1, description="Run test suite")
    router.register("run_formatter",  shell.run_formatter,  min_mode=1, description="Format code")
    router.register("run_linter",     shell.run_linter,     min_mode=1, description="Lint code")
    router.register("install_package",shell.install_package,min_mode=2, description="Install package")

    # Desktop — Mode 2-3
    router.register("capture_screen",     ui.capture_screen,     min_mode=2, description="Take screenshot")
    router.register("get_active_window",  ui.get_active_window,  min_mode=2, description="Get active window title")
    router.register("move_mouse",         ui.move_mouse,         min_mode=3, description="Move mouse cursor")
    router.register("click",              ui.click,              min_mode=3, description="Mouse click")
    router.register("type_text",          ui.type_text,          min_mode=3, description="Type text")
    router.register("hotkey",             ui.hotkey,             min_mode=3, description="Keyboard shortcut")
    router.register("scroll",             ui.scroll,             min_mode=3, description="Scroll mouse wheel")

    logger.info(f"Registered {len(router._registry)} tools")


register_tools()


# ─── WebSocket Broadcast ─────────────────────────────────────────────────────

async def broadcast(event: dict):
    """Send an event to all connected WebSocket clients."""
    msg = json.dumps(event)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = ROOT / "frontend" / "index.html"
    return ui_path.read_text(encoding="utf-8")


@app.get("/api/status")
async def get_status():
    ollama_ok = False
    try:
        from models.ollama_client import OllamaClient
        client = OllamaClient()
        ollama_ok = await client.health_check()
    except Exception:
        pass

    return {
        "agent": "Ken AI offline v0.1.0-skeleton",
        "ollama": ollama_ok,
        "mode": permissions.get_mode_info(),
        "session": session.get_status(),
        "kill_switch": permissions.kill_switch_active(),
        "tools_available": len(router.available_tools()),
        "all_modes": permissions.all_modes(),
    }


@app.get("/api/models")
async def get_models():
    try:
        from models.ollama_client import OllamaClient
        client = OllamaClient()
        models = await client.list_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.post("/api/mode/{mode_num}")
async def set_mode(mode_num: int):
    try:
        permissions.set_mode(mode_num)
        info = permissions.get_mode_info()
        await broadcast({"type": "mode_change", "data": info})
        return {"ok": True, "mode": info}
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/kill_switch/arm")
async def arm_kill():
    permissions.arm_kill_switch()
    await broadcast({"type": "kill_switch", "data": {"active": True}})
    return {"ok": True, "kill_switch": True}


@app.post("/api/kill_switch/disarm")
async def disarm_kill():
    permissions.disarm_kill_switch()
    await broadcast({"type": "kill_switch", "data": {"active": False}})
    return {"ok": True, "kill_switch": False}


@app.post("/api/stop")
async def stop_agent():
    global current_task, planner
    if planner:
        planner.stop()
    if current_task and not current_task.done():
        current_task.cancel()
    await broadcast({"type": "agent_stopped", "data": {}})
    return {"ok": True}


@app.get("/api/brain")
async def get_brain():
    files = memory.list_brain_files()
    return {"files": files}


@app.get("/api/brain/{filename}")
async def get_brain_file(filename: str):
    content = memory.read_brain_file(filename)
    return {"filename": filename, "content": content}


@app.get("/api/tasks")
async def get_tasks():
    return {
        "open": session.list_open_tasks(),
        "status": session.get_status(),
    }


@app.get("/api/tools")
async def get_tools():
    return {
        "available": router.available_tools(),
        "all": list(router._registry.keys()),
        "mode": permissions.mode,
    }


# ─── WebSocket Handler ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_task, planner

    await websocket.accept()
    connections.append(websocket)
    logger.info(f"WebSocket connected. Total: {len(connections)}")

    # Send initial state
    status = await get_status()
    await websocket.send_text(json.dumps({"type": "init", "data": status}))

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "chat":
                user_input = msg.get("text", "").strip()
                if not user_input:
                    continue

                # Stop any running task first
                if current_task and not current_task.done():
                    if planner:
                        planner.stop()
                    current_task.cancel()
                    await asyncio.sleep(0.1)

                # Create planner and run
                planner = Planner(
                    permissions=permissions,
                    memory=memory,
                    session=session,
                    router=router,
                    on_event=broadcast,
                )

                current_task = asyncio.create_task(
                    planner.run_task(user_input)
                )

            elif action == "set_mode":
                mode_num = int(msg.get("mode", 0))
                await set_mode(mode_num)

            elif action == "arm_kill":
                await arm_kill()

            elif action == "disarm_kill":
                await disarm_kill()

            elif action == "stop":
                await stop_agent()

            elif action == "get_status":
                status = await get_status()
                await websocket.send_text(json.dumps({"type": "status", "data": status}))

            elif action == "get_brain":
                files = memory.list_brain_files()
                content = {f: memory.read_brain_file(f) for f in files}
                await websocket.send_text(json.dumps({"type": "brain", "data": content}))

    except WebSocketDisconnect:
        connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining: {len(connections)}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        if websocket in connections:
            connections.remove(websocket)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  OfflineAgent v1.0")
    print("  http://localhost:7777")
    print("  Ollama: http://localhost:11434")
    print("═" * 60 + "\n")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=7777,
        reload=False,
        log_level="info",
    )
