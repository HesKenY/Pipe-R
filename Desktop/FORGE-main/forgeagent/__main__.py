"""ForgeAgent entry point — python -m forgeagent"""
from __future__ import annotations
import asyncio
import json
import shutil
import subprocess
import sys
import os
import time
from pathlib import Path


def _ensure_dirs(config):
    """Create all required directories on startup."""
    for d in [config.memory_dir, config.dreams_dir, config.sessions_dir, config.buddy_dir]:
        Path(d).mkdir(parents=True, exist_ok=True)


def _auto_setup() -> dict:
    """First-launch setup: create .env, check/start Ollama."""
    status = {"env_created": False, "ollama_running": False, "ollama_auto_started": False}
    root = Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    env_example = root / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy2(env_example, env_file)
        status["env_created"] = True
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)

    # Check Ollama
    try:
        import httpx
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3)
        status["ollama_running"] = resp.status_code == 200
    except Exception:
        pass

    # Auto-start Ollama on Windows if not running
    if not status["ollama_running"] and sys.platform == "win32":
        ollama_path = shutil.which("ollama")
        if ollama_path:
            try:
                subprocess.Popen(
                    [ollama_path, "serve"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                status["ollama_auto_started"] = True
                for _ in range(10):
                    time.sleep(1)
                    try:
                        import httpx
                        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2)
                        if resp.status_code == 200:
                            status["ollama_running"] = True
                            break
                    except Exception:
                        pass
            except Exception:
                pass

    return status


def _load_agent_config(project_path: str) -> dict | None:
    """Load agent config from .forgeagent/agent.json in the project."""
    agent_file = Path(project_path) / ".forgeagent" / "agent.json"
    if agent_file.exists():
        try:
            return json.loads(agent_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def main():
    """ForgeAgent — Local AI coding agent hub."""
    import click

    @click.command()
    @click.option("-m", "--model", default=None, help="Override Ollama model")
    @click.option("--cli", is_flag=True, help="Plain text REPL (no TUI)")
    @click.option("--agent", is_flag=True, help="Agent mode — terminal coding agent")
    @click.option("--team", is_flag=True, help="Team mode — all agents in one terminal")
    @click.option("--project", default=None, help="Project path for agent/team mode")
    def run(model: str | None, cli: bool, agent: bool, team: bool, project: str | None):
        setup_status = _auto_setup()

        from .config import load_config
        config = load_config()
        if model:
            config.model = model
        if project:
            config.cwd = str(Path(project).resolve())

        _ensure_dirs(config)

        # Core (always needed)
        from .core.query_engine import QueryEngine
        from .tools.registry import create_tool_registry
        from .commands.registry import create_commands
        from .memory.session_store import MemoryStore, SessionStore
        from .buddy.buddy import Buddy

        tools = create_tool_registry()

        # Agent mode — load agent-specific config and filter tools
        agent_config = None
        if agent:
            agent_config = _load_agent_config(config.cwd)
            if agent_config:
                if not model and agent_config.get("modelName"):
                    config.model = agent_config["modelName"]
                if agent_config.get("systemPrompt"):
                    config.system_prompt = agent_config["systemPrompt"]
                if agent_config.get("temperature"):
                    config.temperature = agent_config["temperature"]
                # Filter tools to only what agent is allowed
                allowed = agent_config.get("tools")
                if allowed:
                    tools = {k: v for k, v in tools.items() if k in allowed}

        engine = QueryEngine(config, tools)
        commands = create_commands()
        memory = MemoryStore(config.memory_dir, config.dreams_dir)
        session_store = SessionStore(config.sessions_dir)
        buddy = Buddy(config.buddy_dir)

        # Training + deploy (lazy)
        from .training.dataset_manager import DatasetManager
        from .training.model_builder import ModelBuilder
        from .training.evaluator import Evaluator
        from .training.web_scraper import WebScrapeCollector
        from .deploy.agent_deployer import AgentDeployer
        from .deploy.instance_manager import InstanceManager

        ctx = {
            "engine": engine, "commands": commands, "config": config,
            "buddy": buddy, "memory": memory, "session_store": session_store,
            "dataset_manager": DatasetManager(config.memory_dir),
            "model_builder": ModelBuilder(config.memory_dir),
            "evaluator": Evaluator(config.memory_dir, config.ollama_base_url),
            "scraper": WebScrapeCollector(config.memory_dir),
            "deployer": AgentDeployer(config.memory_dir),
            "instance_manager": InstanceManager(config.memory_dir, config.ollama_base_url),
            "setup_status": setup_status,
        }

        try:
            if team:
                # Team mode — all models in one terminal
                from .ui.team_cli import start_team_cli
                from .training.model_builder import ModelBuilder
                mb = ModelBuilder(config.memory_dir)
                all_models = [m["name"] for m in mb.list_local_models()]
                if model:
                    # If specific model given, use it plus 3 others
                    team_models = [model] + [m for m in all_models if m != model][:3]
                else:
                    team_models = all_models[:4]
                if not team_models:
                    team_models = [config.model]
                asyncio.run(start_team_cli(team_models, config.cwd, config.ollama_base_url))
            elif agent or cli:
                from .ui.cli import start_agent_cli
                asyncio.run(start_agent_cli(ctx, agent_config))
            else:
                from .ui.tui import start_tui
                asyncio.run(start_tui(ctx))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"\n[!] ForgeAgent error: {e}", file=sys.stderr)
            print(f"    Log: {Path(config.memory_dir) / 'forgeagent.log'}", file=sys.stderr)
            sys.exit(1)

    run()


if __name__ == "__main__":
    main()
