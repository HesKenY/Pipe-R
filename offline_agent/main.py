"""
main.py
KenAI Offline Developer server.
Serves the local coding workbench at http://localhost:7778.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from agent_core.memory_retriever import MemoryRetriever
from agent_core.permissions import PermissionsEngine
from agent_core.planner import Planner
from agent_core.session_manager import SessionManager
from agent_core.squad_state import build_squad_snapshot
from agent_core.tool_router import ToolRouter
from models.ollama_client import OllamaClient
from tools import filesystem_tools as fs
from tools import git_tools as git
from tools import memory_tools as mem
from tools import search_tools as search
from tools import shell_tools as shell
from tools import ui_tools as ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")

ROOT = Path(__file__).parent
CONFIG_DIR = ROOT / "config"
ACTIONS_LOG = ROOT / "logs" / "actions.jsonl"
BRAIN_REFRESH_SECONDS = int(os.environ.get("BRAIN_REFRESH_SECONDS", "1800"))
AGENT_NAME = "KenAI Offline Developer"
AGENT_VERSION = "0.4.1"


async def brain_refresh_loop():
    await asyncio.sleep(5)
    while True:
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                "brain/brain_build.py",
                "--once",
                cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                logger.info("brain auto-refresh ok: %s", (stdout or b"").decode(errors="ignore")[:160])
            else:
                logger.warning("brain auto-refresh failed: %s", (stderr or b"").decode(errors="ignore")[:200])
        except Exception as exc:
            logger.warning("brain auto-refresh exception: %s", exc)
        await asyncio.sleep(BRAIN_REFRESH_SECONDS)


refresh_task: Optional[asyncio.Task] = None
current_task: Optional[asyncio.Task] = None
planner: Optional[Planner] = None
connections: list[WebSocket] = []


async def warm_planner_model():
    try:
        client = OllamaClient(profile="planner")
        if not await client.health_check():
            logger.warning("warmup skipped: ollama not reachable at %s", client.base_url)
            return
        resolution = await client.describe_resolution(refresh=True)
        logger.info("warming planner model: %s", resolution["active_model"])
        await client.chat(
            [{"role": "user", "content": "ready"}],
            system="reply with the single word ok",
        )
    except Exception as exc:
        logger.warning("warmup failed (non-fatal): %s", exc)


async def on_startup():
    global refresh_task
    logger.info("brain auto-refresh scheduled every %ss", BRAIN_REFRESH_SECONDS)
    refresh_task = asyncio.create_task(brain_refresh_loop())
    asyncio.create_task(warm_planner_model())


async def on_shutdown():
    global refresh_task
    if refresh_task and not refresh_task.done():
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION, on_startup=[on_startup], on_shutdown=[on_shutdown])

permissions = PermissionsEngine(initial_mode=0)
memory = MemoryRetriever()
session = SessionManager()
router = ToolRouter(permissions, session)


def load_projects_config() -> dict:
    path = CONFIG_DIR / "projects.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_recent_actions(limit: int = 30) -> list[dict]:
    if not ACTIONS_LOG.exists():
        return []
    rows = []
    for line in ACTIONS_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def register_tools():
    router.register("read_file", fs.read_file, min_mode=0, description="Read a file's contents")
    router.register("list_tree", fs.list_tree, min_mode=0, description="List a directory tree")
    router.register("file_info", fs.file_info, min_mode=0, description="Read file metadata")
    router.register("preview_patch", fs.preview_patch, min_mode=0, description="Preview a write without touching disk")
    router.register("list_pending_patches", fs.list_pending_patches, min_mode=0, description="List pending staged patches")
    router.register("patch_history", fs.patch_history, min_mode=0, description="Read patch history")
    router.register("write_file", fs.write_file, min_mode=1, description="Write a file")
    router.register("apply_patch", fs.apply_patch, min_mode=1, description="Apply a unified diff")
    router.register("apply_multi_patch", fs.apply_multi_patch, min_mode=1, description="Apply a multi-file unified diff")
    router.register("propose_patch", fs.propose_patch, min_mode=1, description="Stage a patch for approval")
    router.register("approve_patch", fs.approve_patch, min_mode=1, description="Approve a staged patch")
    router.register("reject_patch", fs.reject_patch, min_mode=1, description="Reject a staged patch")
    router.register("revert_last_patch", fs.revert_last_patch, min_mode=1, description="Revert the latest backup for a file")
    router.register("delete_file", fs.delete_file, min_mode=2, description="Delete a file after backup")

    router.register("search_repo", search.search_repo, min_mode=0, description="Search a repo")
    router.register("find_files", search.find_files, min_mode=0, description="Find files by pattern")
    router.register("grep_file", search.grep_file, min_mode=0, description="Search inside a file")
    router.register("count_lines", search.count_lines, min_mode=0, description="Count lines in files")

    router.register("git_status", git.git_status, min_mode=0, description="git status")
    router.register("git_diff", git.git_diff, min_mode=0, description="git diff")
    router.register("git_log", git.git_log, min_mode=0, description="git log")
    router.register("git_add", git.git_add, min_mode=1, description="git add")
    router.register("git_commit", git.git_commit, min_mode=1, description="git commit")
    router.register("git_branch", git.git_branch, min_mode=1, description="git branch")
    router.register("git_stash", git.git_stash, min_mode=1, description="git stash")

    router.register("run_command", shell.run_command, min_mode=1, description="Run a shell command")
    router.register("run_tests", shell.run_tests, min_mode=1, description="Run tests")
    router.register("run_formatter", shell.run_formatter, min_mode=1, description="Run formatter")
    router.register("run_linter", shell.run_linter, min_mode=1, description="Run linter")
    router.register("install_package", shell.install_package, min_mode=2, description="Install a package")

    router.register("capture_screen", ui.capture_screen, min_mode=2, description="Take a screenshot")
    router.register("get_active_window", ui.get_active_window, min_mode=2, description="Read the active window title")
    router.register("move_mouse", ui.move_mouse, min_mode=3, description="Move the mouse")
    router.register("click", ui.click, min_mode=3, description="Click the mouse")
    router.register("type_text", ui.type_text, min_mode=3, description="Type text")
    router.register("hotkey", ui.hotkey, min_mode=3, description="Send a hotkey")
    router.register("scroll", ui.scroll, min_mode=3, description="Scroll the mouse wheel")

    router.register("search_brain", mem.search_brain, min_mode=0, description="Search the brain")
    router.register("read_brain_file", mem.read_brain_file, min_mode=0, description="Read one brain file")
    router.register("list_brain_files", mem.list_brain_files, min_mode=0, description="List brain files")
    router.register("brain_stats", mem.brain_stats, min_mode=0, description="Read brain index stats")
    router.register("list_open_tasks", mem.list_open_tasks, min_mode=0, description="List open tasks")
    router.register("read_task", mem.read_task, min_mode=0, description="Read a task")
    router.register("write_brain_file", mem.write_brain_file, min_mode=1, description="Write a brain file")
    router.register("append_session_entry", mem.append_session_entry, min_mode=1, description="Append a session entry")
    router.register("open_task", mem.open_task, min_mode=1, description="Create an open task")
    router.register("close_task", mem.close_task, min_mode=1, description="Close an open task")

    logger.info("Registered %s tools", len(router._registry))


register_tools()


async def broadcast(event: dict):
    message = json.dumps(event)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connections:
            connections.remove(ws)


async def planner_status() -> dict:
    client = OllamaClient(profile="planner")
    ollama_ok = await client.health_check()
    resolution = await client.describe_resolution(refresh=True) if ollama_ok else {
        "profile": "planner",
        "preferred_model": client.preferred_model,
        "active_model": client.preferred_model,
        "fallback_used": False,
        "fallback_chain": client._fallback_chain(),
        "available_models": [],
    }
    return {"ollama": ollama_ok, "planner": resolution}


def workbench_snapshot() -> dict:
    projects_cfg = load_projects_config()
    return {
        "projects": projects_cfg.get("projects", {}),
        "agent": projects_cfg.get("agent", {}),
        "squad": build_squad_snapshot(ROOT, CONFIG_DIR),
        "brain_files": memory.list_brain_files(),
        "tasks": session.list_open_tasks(),
        "tools": router.available_tools(),
        "recent_actions": read_recent_actions(),
    }


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
async def get_status():
    model_status = await planner_status()
    return {
        "agent": f"{AGENT_NAME} {AGENT_VERSION}",
        "version": AGENT_VERSION,
        "mode": permissions.get_mode_info(),
        "session": session.get_status(),
        "kill_switch": permissions.kill_switch_active(),
        "tools_available": len(router.available_tools()),
        "all_modes": permissions.all_modes(),
        **model_status,
    }


@app.get("/api/models")
async def get_models():
    try:
        client = OllamaClient(profile="planner")
        models = await client.list_models()
        resolution = await client.describe_resolution(refresh=True)
        return {"models": models, "planner": resolution}
    except Exception as exc:
        return {"models": [], "error": str(exc)}


@app.get("/api/projects")
async def get_projects():
    cfg = load_projects_config()
    return {"projects": cfg.get("projects", {}), "agent": cfg.get("agent", {})}


@app.get("/api/actions")
async def get_actions(limit: int = 30):
    return {"actions": read_recent_actions(limit)}


@app.get("/api/squad")
async def get_squad():
    return {"squad": build_squad_snapshot(ROOT, CONFIG_DIR)}


@app.get("/api/workbench")
async def get_workbench():
    model_status = await planner_status()
    return {
        "status": await get_status(),
        "workbench": workbench_snapshot(),
        **model_status,
    }


@app.post("/api/mode/{mode_num}")
async def set_mode(mode_num: int):
    try:
        permissions.set_mode(mode_num)
        info = permissions.get_mode_info()
        await broadcast({"type": "mode_change", "data": info})
        return {"ok": True, "mode": info}
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


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
    return {"files": memory.list_brain_files()}


@app.get("/api/brain/{filename}")
async def get_brain_file(filename: str):
    return {"filename": filename, "content": memory.read_brain_file(filename)}


@app.get("/api/tasks")
async def get_tasks():
    return {"open": session.list_open_tasks(), "status": session.get_status()}


@app.get("/api/tools")
async def get_tools():
    return {
        "available": router.available_tools(),
        "all": list(router._registry.keys()),
        "mode": permissions.mode,
    }


@app.get("/api/model_designs")
async def list_model_designs():
    try:
        from brain.model_designer import list_designs

        return {"designs": list_designs()}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/model_designs/{slug}")
async def get_model_design(slug: str):
    try:
        from brain.model_designer import load_design, validate

        design = load_design(slug)
        return {"design": design, "validation": validate(design)}
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/model_designs/{slug}/build")
async def build_model_spec(slug: str):
    try:
        from brain.model_designer import build_dataset, build_training_spec, load_design, save_spec, validate

        design = load_design(slug)
        validation = validate(design)
        if not validation["ok"]:
            return JSONResponse(
                {"ok": False, "validation": validation, "error": "design not valid"},
                status_code=400,
            )
        dataset_path, stats = build_dataset(design)
        spec = build_training_spec(design, dataset_path, stats)
        spec_path = save_spec(design, spec)
        return {"ok": True, "dataset": str(dataset_path), "spec": str(spec_path), "stats": stats}
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/brain/rebuild")
async def rebuild_brain():
    try:
        from tools.win_subprocess import run as win_run

        result = win_run(
            ["python", "brain/brain_build.py", "--once"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": (result.stdout or "")[:2000],
            "stderr": (result.stderr or "")[:500],
        }
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/model_designs/{slug}/modelfile")
async def build_modelfile_api(slug: str, model_name: Optional[str] = None):
    try:
        from brain.modelfile_builder import build_modelfile, latest_dataset_for, load_design

        design = load_design(slug)
        dataset = latest_dataset_for(slug)
        if not dataset:
            return JSONResponse(
                {"error": f"no dataset for {slug} - run POST /api/model_designs/{slug}/build first"},
                status_code=400,
            )
        out_name = model_name or f"{slug.replace('-', '')}v1"
        out_path, stats = build_modelfile(design, dataset, out_name)
        return {"ok": True, "path": str(out_path), **stats}
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/model_designs/{slug}/evaluate")
async def evaluate_model_api(slug: str, model: str, timeout: int = 120):
    try:
        from brain.evaluator import evaluate

        return evaluate(slug, model, timeout_s=timeout)
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/dispatch/tool")
async def dispatch_tool(payload: dict = Body(...)):
    try:
        tool = payload.get("tool")
        params = payload.get("params", {})
        if not tool:
            return JSONResponse({"success": False, "error": "missing tool"}, status_code=400)
        result = await router.call(tool, params)
        return result
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_task, planner

    await websocket.accept()
    connections.append(websocket)
    logger.info("WebSocket connected. Total: %s", len(connections))
    await websocket.send_text(json.dumps({"type": "init", "data": await get_status()}))

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            action = message.get("action")

            if action == "chat":
                user_input = message.get("text", "").strip()
                if not user_input:
                    continue
                if current_task and not current_task.done():
                    if planner:
                        planner.stop()
                    current_task.cancel()
                    await asyncio.sleep(0.1)

                planner = Planner(
                    permissions=permissions,
                    memory=memory,
                    session=session,
                    router=router,
                    on_event=broadcast,
                )
                current_task = asyncio.create_task(planner.run_task(user_input))

            elif action == "set_mode":
                await set_mode(int(message.get("mode", 0)))
            elif action == "arm_kill":
                await arm_kill()
            elif action == "disarm_kill":
                await disarm_kill()
            elif action == "stop":
                await stop_agent()
            elif action == "get_status":
                await websocket.send_text(json.dumps({"type": "status", "data": await get_status()}))
            elif action == "get_workbench":
                await websocket.send_text(json.dumps({"type": "workbench", "data": await get_workbench()}))

    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WebSocket disconnected. Remaining: %s", len(connections))
    except Exception as exc:
        logger.exception("WebSocket error: %s", exc)
        if websocket in connections:
            connections.remove(websocket)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(f"  {AGENT_NAME} {AGENT_VERSION}")
    print("  http://127.0.0.1:7778")
    print("  Ollama: http://127.0.0.1:11434")
    print("=" * 60 + "\n")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=7778,
        reload=False,
        log_level="info",
    )
