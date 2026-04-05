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

    # ── Single agent deploy (legacy compat) ──────────
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
        for sub in ("memory", "sessions", "dreams", "buddy", "agents"):
            (agent_dir / sub).mkdir(parents=True, exist_ok=True)

        (agent_dir / "agent.json").write_text(json.dumps(agent, indent=2), encoding="utf-8")

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
        self._write_launch_script(agent_dir, pp, agent["name"], agent["modelName"])

        # Memory init
        mem = agent_dir / "memory" / "MEMORY.md"
        if not mem.exists():
            mem.write_text(f"# {name} Memory — {pp.name}\n\n## Project\n- Path: {pp}\n- Agent: {name} ({agent['modelName']})\n", encoding="utf-8")

        self._add_to_registry(agent)
        return agent

    # ── Multi-agent deploy (1-6 models) ──────────────
    def deploy_multi(self, project_path: str, models: list[str],
                     template: str | None = None) -> list[dict]:
        """Deploy 1-6 trained models as terminal coding agents in a project."""
        pp = Path(project_path).resolve()
        pp.mkdir(parents=True, exist_ok=True)
        tpl = get_template(template) if template else None

        agent_dir = pp / ".forgeagent"
        for sub in ("memory", "sessions", "dreams", "buddy", "agents"):
            (agent_dir / sub).mkdir(parents=True, exist_ok=True)

        agents = []
        for model_name in models[:6]:
            safe_name = model_name.replace(":", "-").replace("/", "-")
            agent_id = base36_now()
            agent = {
                "id": agent_id,
                "name": f"{safe_name}",
                "modelName": model_name,
                "projectPath": str(pp),
                "template": template,
                "systemPrompt": (tpl or {}).get("systemPrompt",
                    f"You are {safe_name}, a highly capable AI coding assistant. "
                    f"You work on the project at {pp.name}. Use tools proactively to help the user."),
                "temperature": (tpl or {}).get("temperature", 0.7),
                "tools": (tpl or {}).get("tools", [
                    "bash", "read_file", "write_file", "edit_file",
                    "list_dir", "search_files", "glob", "web_fetch",
                    "task", "datetime", "memory_save", "memory_search",
                ]),
                "created": datetime.now().isoformat(),
                "status": "ready",
            }

            # Per-agent config file
            agent_config_path = agent_dir / "agents" / f"{safe_name}.json"
            agent_config_path.write_text(json.dumps(agent, indent=2), encoding="utf-8")

            # Also write as agent.json if first model (primary agent)
            if not agents:
                (agent_dir / "agent.json").write_text(json.dumps(agent, indent=2), encoding="utf-8")

            # Per-agent launch script
            self._write_agent_launch_script(agent_dir, pp, safe_name, model_name)

            self._add_to_registry(agent)
            agents.append(agent)

        # Write a launch-all script
        self._write_launch_all_script(agent_dir, pp, agents)

        # Write shared .env
        primary = agents[0] if agents else {}
        env = f"""OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL={primary.get('modelName', 'forgeagent')}
TEMPERATURE={primary.get('temperature', 0.7)}
MAX_TOOL_ROUNDS=8
MAX_TOOL_CALLS_PER_TURN=4
DREAM_INTERVAL=10
MEMORY_DIR=.forgeagent/memory
"""
        (agent_dir / ".env").write_text(env, encoding="utf-8")

        # Memory init
        mem = agent_dir / "memory" / "MEMORY.md"
        if not mem.exists():
            model_list = ", ".join(a["modelName"] for a in agents)
            mem.write_text(
                f"# Project Memory — {pp.name}\n\n"
                f"## Agents\n- {model_list}\n"
                f"## Project\n- Path: {pp}\n",
                encoding="utf-8",
            )

        return agents

    # ── Launch helpers ────────────────────────────────
    def launch_multi(self, project_path: str, models: list[str]) -> list[dict]:
        """Open a terminal window for each model as a coding agent."""
        pp = Path(project_path).resolve()
        results = []
        for model_name in models[:6]:
            safe_name = model_name.replace(":", "-").replace("/", "-")
            result = self._launch_agent_terminal(pp, safe_name, model_name)
            results.append(result)
            # Update registry status
            self.update_agent(safe_name, {"status": "running", "lastLaunched": datetime.now().isoformat()})
        return results

    def _launch_agent_terminal(self, pp: Path, safe_name: str, model_name: str) -> dict:
        """Open one terminal window for an agent."""
        agent_dir = pp / ".forgeagent"
        is_win = sys.platform == "win32"
        project_name = pp.name
        try:
            if is_win:
                bat = agent_dir / f"launch-{safe_name}.bat"
                if not bat.exists():
                    # Fallback: create on the fly
                    self._write_agent_launch_script(agent_dir, pp, safe_name, model_name)
                subprocess.Popen(
                    f'start "ForgeAgent — {safe_name} @ {project_name}" cmd /c "{bat}"',
                    shell=True, cwd=str(pp),
                )
            else:
                sh = agent_dir / f"launch-{safe_name}.sh"
                if not sh.exists():
                    self._write_agent_launch_script(agent_dir, pp, safe_name, model_name)
                subprocess.Popen(["bash", str(sh)], cwd=str(pp))
            return {"success": True, "model": model_name, "message": f"Launched {safe_name}"}
        except Exception as e:
            return {"success": False, "model": model_name, "message": f"Failed: {e}"}

    def launch(self, agent_id: str) -> dict:
        agent = self.find_agent(agent_id)
        if not agent:
            return {"success": False, "message": f'Agent "{agent_id}" not found'}
        pp = Path(agent["projectPath"])
        safe_name = agent["name"]
        model_name = agent.get("modelName", "forgeagent")
        result = self._launch_agent_terminal(pp, safe_name, model_name)
        if result["success"]:
            self.update_agent(agent["id"], {"status": "running", "lastLaunched": datetime.now().isoformat()})
        return result

    # ── Script generation ────────────────────────────
    def _write_agent_launch_script(self, agent_dir: Path, pp: Path, safe_name: str, model_name: str):
        """Generate launch scripts that start the agent CLI mode."""
        bat = f"""@echo off
title ForgeAgent — {safe_name} @ {pp.name}
color 0B
echo.
echo   ===================================
echo    ForgeAgent Agent: {safe_name}
echo    Model: {model_name}
echo    Project: {pp.name}
echo   ===================================
echo.
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 ( start "" ollama serve >nul 2>&1 & timeout /t 3 /nobreak >nul )
cd /d "{pp}"
set FORGEAGENT_HOME={pp}
set DOTENV_CONFIG_PATH={agent_dir / '.env'}
python -m forgeagent --agent --project "{pp}" -m {model_name}
pause
"""
        (agent_dir / f"launch-{safe_name}.bat").write_text(bat, encoding="utf-8")

        sh = f"""#!/bin/bash
echo ""
echo "  ==================================="
echo "   ForgeAgent Agent: {safe_name}"
echo "   Model: {model_name}"
echo "   Project: {pp.name}"
echo "  ==================================="
echo ""
pgrep -x ollama > /dev/null || {{ ollama serve & sleep 3; }}
cd "{pp}"
FORGEAGENT_HOME="{pp}" python -m forgeagent --agent --project "{pp}" -m {model_name}
"""
        (agent_dir / f"launch-{safe_name}.sh").write_text(sh, encoding="utf-8")

    def _write_launch_script(self, agent_dir: Path, pp: Path, name: str, model_name: str):
        """Legacy single-agent launch script."""
        self._write_agent_launch_script(agent_dir, pp, name, model_name)

    def _write_launch_all_script(self, agent_dir: Path, pp: Path, agents: list[dict]):
        """Generate a script that launches all agents at once."""
        lines_bat = ["@echo off", f"title ForgeAgent — All Agents @ {pp.name}", "echo Launching all agents...", ""]
        lines_sh = ["#!/bin/bash", f'echo "Launching all agents for {pp.name}..."', ""]

        for agent in agents:
            safe = agent["name"]
            lines_bat.append(f'start "ForgeAgent — {safe}" cmd /c "{agent_dir / f"launch-{safe}.bat"}"')
            lines_bat.append("timeout /t 2 /nobreak >nul")
            lines_sh.append(f'bash "{agent_dir / f"launch-{safe}.sh"}" &')
            lines_sh.append("sleep 2")

        lines_bat.extend(["", "echo All agents launched.", "pause"])
        lines_sh.extend(["", 'echo "All agents launched."', "wait"])

        (agent_dir / "launch-all.bat").write_text("\n".join(lines_bat), encoding="utf-8")
        (agent_dir / "launch-all.sh").write_text("\n".join(lines_sh), encoding="utf-8")

    # ── Registry management ──────────────────────────
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

    def get_agents_for_project(self, project_path: str) -> list[dict]:
        """Get all agents deployed to a specific project."""
        pp = str(Path(project_path).resolve())
        return [a for a in self._load_registry() if a.get("projectPath") == pp]

    def _load_registry(self) -> list[dict]:
        try:
            return json.loads(self.registry_file.read_text())
        except Exception:
            return []

    def _save_registry(self, agents: list[dict]) -> None:
        self.registry_file.write_text(json.dumps(agents, indent=2), encoding="utf-8")

    def _add_to_registry(self, agent: dict) -> None:
        agents = self._load_registry()
        agents = [a for a in agents if a.get("id") != agent["id"]]
        agents.append(agent)
        self._save_registry(agents)
