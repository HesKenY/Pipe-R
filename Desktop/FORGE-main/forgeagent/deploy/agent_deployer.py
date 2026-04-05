"""Deploy agents to project folders with .forgeagent/ config."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from .templates import get_template
from ..utils.helpers import base36_now


class AgentDeployer:
    def __init__(self, base_dir: str):
        self.registry_dir = Path(base_dir) / "deployed"
        self.registry_file = self.registry_dir / "registry.json"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self.registry_file.write_text("[]", encoding="utf-8")

    def deploy(self, name: str, project_path: str, model_name: str = "forgeagent",
               template: str | None = None) -> dict:
        pp = Path(project_path).resolve()
        pp.mkdir(parents=True, exist_ok=True)
        tpl = get_template(template) if template else None
        agent = {
            "id": base36_now(), "name": name, "modelName": model_name or (tpl or {}).get("baseModel", "forgeagent"),
            "projectPath": str(pp), "template": template,
            "systemPrompt": (tpl or {}).get("systemPrompt", f"You are {name}, a coding assistant."),
            "temperature": (tpl or {}).get("temperature", 0.7),
            "tools": (tpl or {}).get("tools", ["bash", "read_file", "write_file", "edit_file", "list_dir", "search_files", "glob", "web_fetch", "task", "datetime", "memory_save", "memory_search"]),
            "created": datetime.now().isoformat(), "status": "ready",
        }

        agent_dir = pp / ".forgeagent"
        for sub in ("memory", "sessions", "dreams", "buddy"):
            (agent_dir / sub).mkdir(parents=True, exist_ok=True)

        (agent_dir / "agent.json").write_text(json.dumps(agent, indent=2, encoding="utf-8"), encoding="utf-8")

        # .env
        env = f"""OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL={agent['modelName']}
TEMPERATURE={agent['temperature']}
MAX_TOOL_ROUNDS=8
MAX_TOOL_CALLS_PER_TURN=4
DREAM_INTERVAL=10
MEMORY_DIR=.forgeagent/memory
DREAMS_DIR=.forgeagent/dreams
SESSIONS_DIR=.forgeagent/sessions
BUDDY_DIR=.forgeagent/buddy
"""
        (agent_dir / ".env").write_text(env, encoding="utf-8")

        # Launch scripts
        forge_root = str(Path(__file__).resolve().parent.parent.parent)
        bat = f"""@echo off
title ForgeAgent - {name}
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 ( start "" ollama serve >nul 2>&1 & timeout /t 3 >nul )
cd /d "{pp}"
set FORGEAGENT_HOME={pp}
set DOTENV_CONFIG_PATH={agent_dir / '.env'}
python -m forgeagent %*
pause
"""
        (agent_dir / "launch.bat").write_text(bat, encoding="utf-8")

        sh = f"""#!/bin/bash
pgrep -x ollama > /dev/null || {{ ollama serve & sleep 3; }}
cd "{pp}"
FORGEAGENT_HOME="{pp}" python -m forgeagent "$@"
"""
        (agent_dir / "launch.sh").write_text(sh, encoding="utf-8")

        # Memory init
        mem = agent_dir / "memory" / "MEMORY.md"
        if not mem.exists():
            mem.write_text(f"# {name} Memory — {pp.name}\n\n## Project\n- Path: {pp}\n- Agent: {name} ({agent['modelName']})\n", encoding="utf-8")

        self._add_to_registry(agent)
        return agent

    def undeploy(self, agent_id: str, remove_files: bool = False) -> bool:
        agents = self._load_registry()
        idx = next((i for i, a in enumerate(agents) if a["id"] == agent_id or a["name"] == agent_id), None)
        if idx is None:
            return False
        agent = agents.pop(idx)
        self._save_registry(agents)
        if remove_files:
            import shutil
            ad = Path(agent["projectPath"]) / ".forgeagent"
            if ad.exists():
                shutil.rmtree(ad)
        return True

    def launch(self, agent_id: str) -> dict:
        agent = self.find_agent(agent_id)
        if not agent:
            return {"success": False, "message": f'Agent "{agent_id}" not found'}
        ad = Path(agent["projectPath"]) / ".forgeagent"
        is_win = sys.platform == "win32"
        try:
            if is_win:
                bat = ad / "launch.bat"
                if not bat.exists():
                    return {"success": False, "message": "Launch script not found."}
                subprocess.Popen(f'start "ForgeAgent — {agent["name"]}" cmd /c "{bat}"',
                                 shell=True, cwd=agent["projectPath"])
            else:
                sh = ad / "launch.sh"
                subprocess.Popen(["bash", str(sh)], cwd=agent["projectPath"])
            self.update_agent(agent["id"], {"status": "running", "lastLaunched": datetime.now().isoformat()})
            return {"success": True, "message": f"Launched {agent['name']} in {agent['projectPath']}"}
        except Exception as e:
            return {"success": False, "message": f"Launch failed: {e}"}

    def list_agents(self) -> list[dict]:
        return sorted(self._load_registry(), key=lambda a: a.get("created", ""), reverse=True)

    def find_agent(self, id_or_name: str) -> dict | None:
        for a in self._load_registry():
            if a.get("id") == id_or_name or a.get("name") == id_or_name or a.get("id", "").startswith(id_or_name):
                return a
        return None

    def get_agent_info(self, id_or_name: str) -> dict | None:
        agent = self.find_agent(id_or_name)
        if not agent:
            return None
        ad = Path(agent["projectPath"]) / ".forgeagent"
        mem_path = ad / "memory" / "MEMORY.md"
        sess_dir = ad / "sessions"
        return {
            "agent": agent, "hasConfig": (ad / "agent.json").exists(),
            "hasMemory": mem_path.exists(),
            "memorySize": mem_path.stat().st_size if mem_path.exists() else 0,
            "sessionCount": len(list(sess_dir.glob("*.json"))) if sess_dir.exists() else 0,
        }

    def update_agent(self, id_or_name: str, updates: dict) -> bool:
        agents = self._load_registry()
        for a in agents:
            if a.get("id") == id_or_name or a.get("name") == id_or_name:
                a.update(updates)
                self._save_registry(agents)
                return True
        return False

    def _load_registry(self) -> list[dict]:
        try:
            return json.loads(self.registry_file.read_text())
        except Exception:
            return []

    def _save_registry(self, agents: list[dict]) -> None:
        self.registry_file.write_text(json.dumps(agents, indent=2, encoding="utf-8"), encoding="utf-8")

    def _add_to_registry(self, agent: dict) -> None:
        agents = self._load_registry()
        agents = [a for a in agents if a.get("id") != agent["id"]]
        agents.append(agent)
        self._save_registry(agents)
