"""
main.py
KenAI — Ken's local coding agent server.
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
from tools import memory_tools as mem
from tools import drill_tools as drill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("main")

# ─── Bootstrap ───────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

# Brain auto-refresh cadence — run brain_build.py --once on this
# schedule so imports from Claude/Pipe-R/halo-trainer stay fresh
# while the server is up. 30 min default.
BRAIN_REFRESH_SECONDS = int(os.environ.get("BRAIN_REFRESH_SECONDS", "1800"))


async def brain_refresh_loop():
    """Background task: periodically rerun brain_build.py and rebuild FTS."""
    # First pass waits a bit so the server is fully up
    await asyncio.sleep(5)
    while True:
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "brain/brain_build.py", "--once",
                cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                logger.info("brain auto-refresh ok")
            else:
                logger.warning(f"brain auto-refresh failed: {(stderr or b'').decode(errors='ignore')[:200]}")
        except Exception as e:
            logger.warning(f"brain auto-refresh exception: {e}")
        await asyncio.sleep(BRAIN_REFRESH_SECONDS)


_refresh_task: Optional[asyncio.Task] = None


async def warm_planner_model():
    """
    Fire a trivial chat at the planner model once at boot so
    the first real request doesn't eat a 15-45s cold load.
    Non-fatal — logs a warning if ollama isn't ready yet.
    """
    try:
        from models.ollama_client import OllamaClient
        client = OllamaClient(profile="planner")
        if not await client.health_check():
            logger.warning(f"warmup skipped: ollama not reachable at {client.base_url}")
            return
        logger.info(f"warming {client.model} ...")
        await client.chat(
            [{"role": "user", "content": "ready"}],
            system="reply with the single word ok",
        )
        logger.info(f"warmup ok: {client.model} loaded")
    except Exception as e:
        logger.warning(f"warmup failed (non-fatal): {e}")


async def on_startup():
    global _refresh_task
    logger.info(f"brain auto-refresh scheduled every {BRAIN_REFRESH_SECONDS}s")
    _refresh_task = asyncio.create_task(brain_refresh_loop())
    # Warm the planner model in the background so the first
    # real chat turn isn't a 30s cold load. Doesn't block boot.
    asyncio.create_task(warm_planner_model())


async def on_shutdown():
    global _refresh_task
    if _refresh_task and not _refresh_task.done():
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="KenAI", version="0.1.0", on_startup=[on_startup], on_shutdown=[on_shutdown])

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

    # Brain / memory — Mode 0 read, Mode 1 write to brain/
    router.register("search_brain",        mem.search_brain,        min_mode=0, description="FTS across brain_index + sessions + tasks")
    router.register("read_brain_file",     mem.read_brain_file,     min_mode=0, description="Read one brain_index/*.md file")
    router.register("list_brain_files",    mem.list_brain_files,    min_mode=0, description="List all brain_index files")
    router.register("brain_stats",         mem.brain_stats,         min_mode=0, description="FTS table row counts")
    router.register("list_open_tasks",     mem.list_open_tasks,     min_mode=0, description="List open task files")
    router.register("read_task",           mem.read_task,           min_mode=0, description="Read one task file (open|done)")
    router.register("write_brain_file",    mem.write_brain_file,    min_mode=1, description="Overwrite a brain_index/*.md file")
    router.register("append_session_entry",mem.append_session_entry,min_mode=1, description="Append to today's session log")
    router.register("open_task",           mem.open_task,           min_mode=1, description="Create a new open task file")
    router.register("close_task",          mem.close_task,          min_mode=1, description="Move open task → done with summary")

    # Halo-trainer bridge — Mode 0 read, Mode 1 run
    router.register("list_drills",           drill.list_drills,           min_mode=0, description="List halo-trainer drill definitions")
    router.register("read_drill",            drill.read_drill,            min_mode=0, description="Read one drill's JSON by id")
    router.register("read_run",              drill.read_run,              min_mode=0, description="Read last N run rows for a drill")
    router.register("scoreboard",            drill.scoreboard,            min_mode=0, description="Run halo-trainer scoreboard")
    router.register("curated_corpus_summary",drill.curated_corpus_summary,min_mode=0, description="Row counts of curated corpus per curriculum")
    router.register("run_drill",             drill.run_drill,             min_mode=1, description="Execute one drill or all drills")
    router.register("retry_failed_drills",   drill.retry_failed_drills,   min_mode=1, description="Re-run only drills whose last attempt failed")

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
        "agent": "KenAI v0.1.0",
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


# ─── Model Designer endpoints ────────────────────────────

@app.get("/api/model_designs")
async def list_model_designs():
    """List every design.json under brain/model_designs/."""
    try:
        from brain.model_designer import list_designs
        return {"designs": list_designs()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/model_designs/{slug}")
async def get_model_design(slug: str):
    try:
        from brain.model_designer import load_design, validate
        design = load_design(slug)
        return {"design": design, "validation": validate(design)}
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/model_designs/{slug}/build")
async def build_model_spec(slug: str):
    """Validate → build dataset → emit training spec."""
    try:
        from brain.model_designer import (
            load_design, validate, build_dataset, build_training_spec, save_spec,
        )
        design = load_design(slug)
        v = validate(design)
        if not v["ok"]:
            return JSONResponse(
                {"ok": False, "validation": v, "error": "design not valid"},
                status_code=400,
            )
        ds_path, stats = build_dataset(design)
        spec = build_training_spec(design, ds_path, stats)
        spec_path = save_spec(design, spec)
        return {
            "ok":      True,
            "dataset": str(ds_path),
            "spec":    str(spec_path),
            "stats":   stats,
        }
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/brain/rebuild")
async def rebuild_brain():
    """Re-run the import manifest + rebuild FTS."""
    try:
        from tools.win_subprocess import run as _win_run
        res = _win_run(
            ["python", "brain/brain_build.py", "--once"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok":     res.returncode == 0,
            "stdout": (res.stdout or "")[:2000],
            "stderr": (res.stderr or "")[:500],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/model_designs/{slug}/modelfile")
async def build_modelfile_api(slug: str, model_name: Optional[str] = None):
    """Emit an Ollama Modelfile from a design + its latest dataset."""
    try:
        from brain.modelfile_builder import load_design, latest_dataset_for, build_modelfile
        design = load_design(slug)
        ds = latest_dataset_for(slug)
        if not ds:
            return JSONResponse(
                {"error": f"no dataset for {slug} — run POST /api/model_designs/{slug}/build first"},
                status_code=400,
            )
        name = model_name or f"{slug.replace('-', '')}v1"
        out_path, stats = build_modelfile(design, ds, name)
        return {"ok": True, **stats}
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/model_designs/{slug}/evaluate")
async def evaluate_model_api(slug: str, model: str, timeout: int = 120):
    """Run the evaluator against a given ollama model tag."""
    try:
        from brain.evaluator import evaluate
        report = evaluate(slug, model, timeout_s=timeout)
        return report
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── Halo tab endpoints ──────────────────────────────────

@app.post("/api/halo/aimbot/start")
async def halo_aimbot_start():
    from tools.halo_actions import aimbot_start
    return aimbot_start()


@app.post("/api/halo/aimbot/stop")
async def halo_aimbot_stop():
    from tools.halo_actions import aimbot_stop
    return aimbot_stop()


@app.get("/api/halo/aimbot/stats")
async def halo_aimbot_stats():
    from tools.halo_actions import aimbot_stats
    return aimbot_stats()


@app.post("/api/halo/hunt/delta")
async def halo_hunt_delta():
    from tools.halo_actions import halo_hunt_start
    return halo_hunt_start()


@app.post("/api/halo/hunt/vision")
async def halo_hunt_vision():
    from tools.halo_actions import halo_vision_hunt_start
    return halo_vision_hunt_start()


# Pipe-R halo stack endpoints removed — KenAI is the only
# halo system now (2026-04-14). The bats are still on disk
# but nothing in KenAI wires them.


# ─── KenAI native learning endpoints ─────────────────────

@app.post("/api/halo/keylog/on")
async def halo_keylog_on():
    from tools.halo_actions import keylog_start
    return keylog_start()


@app.post("/api/halo/keylog/off")
async def halo_keylog_off():
    from tools.halo_actions import keylog_stop
    return keylog_stop()


@app.post("/api/halo/vision/on")
async def halo_vision_on():
    from tools.halo_actions import vision_observe_start
    return vision_observe_start()


@app.post("/api/halo/vision/off")
async def halo_vision_off():
    from tools.halo_actions import vision_observe_stop
    return vision_observe_stop()


@app.post("/api/halo/driver/on")
async def halo_driver_on():
    from tools.halo_actions import driver_start
    return driver_start()


@app.post("/api/halo/driver/off")
async def halo_driver_off():
    from tools.halo_actions import driver_stop
    return driver_stop()


@app.post("/api/halo/overnight/start")
async def halo_overnight_start():
    """Master overnight learn mode: keylog + vision + aimbot + driver + next mission."""
    from tools.halo_actions import overnight_learn_start
    return overnight_learn_start()


@app.post("/api/halo/overnight/stop")
async def halo_overnight_stop():
    from tools.halo_actions import overnight_learn_stop
    return overnight_learn_stop()


@app.get("/api/halo/learning/status")
async def halo_learning_status():
    from tools.halo_actions import learning_status
    return learning_status()


@app.post("/api/halo/training/run")
async def halo_training_run(design_slug: str = "ken-ai-offline-v0"):
    """Full training pipeline: brain refresh → dataset → modelfile."""
    from tools.halo_actions import halo_training_run as _run
    return _run(design_slug)


@app.get("/api/halo/corpus/stats")
async def halo_corpus_stats():
    from tools.halo_actions import halo_corpus_stats
    return halo_corpus_stats()


# ─── Halo mission tracker ────────────────────────────────

@app.get("/api/halo/missions")
async def halo_missions_status():
    from tools.halo_missions import get_status
    return get_status()


@app.post("/api/halo/missions/{slug}/start")
async def halo_mission_start(slug: str):
    from tools.halo_missions import start_mission
    return start_mission(slug)


@app.post("/api/halo/missions/{slug}/complete")
async def halo_mission_complete(slug: str, notes: str = ""):
    from tools.halo_missions import mark_complete
    return mark_complete(slug, notes)


@app.post("/api/halo/missions/complete")
async def halo_mission_complete_current(notes: str = ""):
    """Mark whichever mission is currently in-progress as complete."""
    from tools.halo_missions import mark_complete
    return mark_complete(None, notes)


@app.post("/api/halo/missions/{slug}/skip")
async def halo_mission_skip(slug: str, reason: str = ""):
    from tools.halo_missions import skip_mission
    return skip_mission(slug, reason)


@app.post("/api/halo/missions/reset")
async def halo_mission_reset():
    from tools.halo_missions import reset_progress
    return reset_progress()


@app.post("/api/halo/missions/death")
async def halo_mission_death():
    from tools.halo_missions import log_death
    return log_death()


@app.post("/api/dispatch/tool")
async def dispatch_tool(tool: str, params: Optional[dict] = None):
    """
    Direct tool router call from the UI. Bypasses the planner
    so halo buttons can fire drill_tools / memory_tools without
    going through the chat loop.
    """
    try:
        result = await router.call(tool, params or {})
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/halo/keylog/scrub")
async def halo_keylog_scrub(dry: bool = False):
    """Strip obvious terminal chatter from the halo keylog."""
    try:
        from tools.keylog_scrubber import scrub_all
        return scrub_all(dry_run=dry)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/halo/keylog/start")
async def halo_keylog_start():
    """
    Start the Pipe-R halo keylogger subprocess. This hits the
    running Pipe-R server (Pipe-R owns the keylog + the observe
    loop). KenAI ONLY launches the aimbot directly — the full
    keylog + vision + dumper stack runs inside Pipe-R so both
    sides can read the outputs.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.post("http://127.0.0.1:7777/api/halo/keylog/start", json={})
                return {"ok": True, "source": "pipe-r", "response": r.json()}
            except Exception as e:
                return {"ok": False, "error": f"pipe-r not reachable: {e}", "hint": "start the Pipe-R server (Codex/server.js) on :7777 first"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/halo/learning/start")
async def halo_learning_start():
    """
    Master button — fire KenAI's halo learning stack:
      1. aimbot on (native, halo_tools/scripts/ken_aimbot.py)
      2. mark next unlocked mission as in-progress
    KenAI is the only halo system now — Pipe-R halo stack
    was removed from this orchestration on 2026-04-14.
    """
    from tools.halo_actions import aimbot_start
    from tools.halo_missions import get_status, start_mission

    results = {"started_at": datetime.now().isoformat(timespec="seconds"), "steps": []}

    # 1. aimbot
    r1 = aimbot_start()
    results["steps"].append({"step": "aimbot_start", **r1})

    # 2. mission state — if nothing in-progress, start the next unlocked
    mstatus = get_status()
    if not mstatus.get("current_mission"):
        next_mission = None
        for m in mstatus["missions"]:
            if m["status"] == "unlocked":
                next_mission = m
                break
        if next_mission:
            r3 = start_mission(next_mission["slug"])
            results["steps"].append({"step": "mission_start", **r3})
        else:
            results["steps"].append({"step": "mission_start", "ok": False, "error": "no unlocked mission available"})
    else:
        results["steps"].append({"step": "mission_start", "ok": True, "note": f"already in-progress: {mstatus['current_mission']}"})

    results["ok"] = all(s.get("ok", True) for s in results["steps"])
    results["mission_status"] = get_status()
    return results


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
    # ASCII-only banner — Windows cp1252 console can't render
    # box-drawing unicode without a utf-8 reconfigure.
    print("\n" + "=" * 60)
    print("  KenAI v0.1.0")
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
