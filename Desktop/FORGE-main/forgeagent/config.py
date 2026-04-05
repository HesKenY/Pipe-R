"""Application configuration loaded from .env and environment."""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    ollama_base_url: str = "http://127.0.0.1:11434"
    model: str = "forgeagent"
    system_prompt: str = (
        "You are ForgeAgent, an AI coding agent. You MUST use tools to complete tasks. "
        "NEVER just describe what to do — use write_file, edit_file, bash, and read_file tools to actually make changes. "
        "When asked to create a file, respond with a write_file tool call containing the full file content. "
        "When asked to modify code, use read_file first then edit_file. "
        "Always respond with tool calls in ```tool blocks."
    )
    temperature: float = 0.7
    max_tool_rounds: int = 12
    max_tool_calls_per_turn: int = 6
    dream_interval: int = 10
    cwd: str = field(default_factory=os.getcwd)
    # Directories — all under base
    base_dir: str = ""
    memory_dir: str = ""
    dreams_dir: str = ""
    sessions_dir: str = ""
    buddy_dir: str = ""

    def __post_init__(self):
        base = Path(os.environ.get("FORGEAGENT_HOME", os.getcwd()))
        self.base_dir = str(base)
        mem = base / os.environ.get("MEMORY_DIR", ".memory")
        self.memory_dir = str(mem)
        self.dreams_dir = str(mem / "dreams")
        self.sessions_dir = str(mem / "sessions")
        self.buddy_dir = str(mem / "buddy")


def load_config() -> AppConfig:
    return AppConfig(
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        model=os.environ.get("OLLAMA_MODEL", "forgeagent"),
        system_prompt=os.environ.get(
            "SYSTEM_PROMPT",
            "You are ForgeAgent, an AI coding agent. You MUST use tools to complete tasks. "
            "NEVER just describe what to do — use write_file, edit_file, bash, and read_file tools to actually make changes. "
            "When asked to create a file, respond with a write_file tool call containing the full file content. "
            "When asked to modify code, use read_file first then edit_file. "
            "Always respond with tool calls in ```tool blocks.",
        ),
        temperature=float(os.environ.get("TEMPERATURE", "0.7")),
        max_tool_rounds=int(os.environ.get("MAX_TOOL_ROUNDS", "8")),
        max_tool_calls_per_turn=int(os.environ.get("MAX_TOOL_CALLS_PER_TURN", "4")),
        dream_interval=int(os.environ.get("DREAM_INTERVAL", "10")),
    )
