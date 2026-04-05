"""ForgeAgent entry point — python -m forgeagent"""
from __future__ import annotations
import asyncio
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
        # Reload so dotenv picks up the new file
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
                # Wait for Ollama to become ready
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


def main():
    """ForgeAgent — Local AI coding agent hub."""
    import click

    @click.command()
    @click.option("-m", "--model", default=None, help="Override Ollama model")
    @click.option("--cli", is_flag=True, help="Plain text REPL (no TUI)")
    def run(model: str | None, cli: bool):
        setup_status = _auto_setup()

        from .config import load_config
        config = load_config()
        if model:
            config.model = model
        _ensure_dirs(config)

        # Core (always needed)
        from .core.query_engine import QueryEngine
        from .tools.registry import create_tool_registry
        from .commands.registry import create_commands
        from .memory.session_store import MemoryStore, SessionStore
        from .buddy.buddy import Buddy

        tools = create_tool_registry()
        engine = QueryEngine(config, tools)
        commands = create_commands()
        memory = MemoryStore(config.memory_dir, config.dreams_dir)
        session_store = SessionStore(config.sessions_dir)
        buddy = Buddy(config.buddy_dir)

        # Training + deploy (lazy — only imported here, not at module top)
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
            if cli:
                from .ui.cli import start_cli
                asyncio.run(start_cli(ctx))
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
