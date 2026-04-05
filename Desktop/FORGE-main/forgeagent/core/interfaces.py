"""Tool and Command contracts."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Tool ─────────────────────────────────────────────────────
@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolContext:
    cwd: str
    memory_dir: str


class Tool(ABC):
    definition: ToolDefinition

    @abstractmethod
    async def run(self, inp: dict[str, Any], ctx: ToolContext) -> str: ...


ToolRegistry = dict[str, Tool]


# ── Messages ─────────────────────────────────────────────────
@dataclass
class ChatMessage:
    id: str
    role: str  # system | user | assistant | tool
    content: str
    timestamp: str
    name: str | None = None


@dataclass
class ToolCall:
    tool_name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelTurnResult:
    assistant_message: ChatMessage
    tool_calls: list[ToolCall]
    tool_rounds: int


# ── Command ──────────────────────────────────────────────────
@dataclass
class CommandResult:
    handled: bool = True
    output: str | None = None
    should_exit: bool = False


class CommandContext:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name: str) -> Any:
        return None


class Command(ABC):
    name: str
    aliases: list[str] = []
    description: str = ""

    @abstractmethod
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult: ...
