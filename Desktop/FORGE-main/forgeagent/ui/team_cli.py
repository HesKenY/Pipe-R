"""Unified multi-agent terminal — all agents in one window, one chat input.

All loaded models receive the same prompt. They see each other's responses.
User types once, all agents respond. Agents build on each other's work.
"""
from __future__ import annotations
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.markdown import Markdown
from rich import box

from ..providers.ollama.client import OllamaClient
from ..providers.ollama.tool_protocol import build_tool_instructions, parse_tool_calls
from ..core.interfaces import ChatMessage, ToolContext
from ..tools.registry import create_tool_registry
from ..utils.helpers import make_id

console = Console()

CYAN = "#00e5ff"
PURPLE = "#7c4dff"
GREEN = "#00e676"
RED = "#ff1744"
AMBER = "#ffd740"
DIM = "#5c6b7a"

# Color per agent slot
AGENT_COLORS = ["#00e5ff", "#7c4dff", "#00e676", "#ffd740", "#ff6e40", "#e040fb"]
AGENT_ICONS = ["A1", "A2", "A3", "A4", "A5", "A6"]


class AgentSlot:
    """One agent in the team — its own model, history, identity."""

    def __init__(self, slot: int, model_name: str, client: OllamaClient,
                 tools: dict, cwd: str, system_prompt: str):
        self.slot = slot
        self.model = model_name
        self.client = client
        self.tools = tools
        self.cwd = cwd
        self.color = AGENT_COLORS[slot % len(AGENT_COLORS)]
        self.icon = AGENT_ICONS[slot % len(AGENT_ICONS)]
        self.history: list[ChatMessage] = [
            ChatMessage(
                id=make_id(), role="system",
                content=system_prompt + "\n\n" + build_tool_instructions(list(tools.values())),
                timestamp=datetime.now().isoformat(),
            )
        ]
        self.total_tools = 0

    async def send(self, message: str, shared_context: str = "") -> dict:
        """Send a message to this agent. Returns {response, tool_calls, tools_used}."""
        now = datetime.now().isoformat()

        # Include shared context from other agents
        full_message = message
        if shared_context:
            full_message = (
                f"{message}\n\n"
                f"[Context from other agents on this team — build on their work, don't repeat it]\n"
                f"{shared_context}"
            )

        self.history.append(ChatMessage(id=make_id(), role="user", content=full_message, timestamp=now))

        all_tool_calls = []
        rounds = 0

        while rounds < 8:
            rounds += 1
            try:
                response = await self.client.chat(
                    model=self.model,
                    messages=self.history,
                    temperature=0.7,
                )
            except Exception as e:
                response = f"Error: {e}"
                break

            assistant_text, tool_calls = parse_tool_calls(response)

            if not tool_calls:
                text = assistant_text or response
                self.history.append(ChatMessage(id=make_id(), role="assistant", content=text, timestamp=now))
                return {"response": text, "tool_calls": all_tool_calls, "tools_used": [tc.tool_name for tc in all_tool_calls]}

            # Execute tools
            self.history.append(ChatMessage(id=make_id(), role="assistant", content=response, timestamp=now))
            for call in tool_calls[:4]:
                tool = self.tools.get(call.tool_name)
                if tool:
                    try:
                        result = await tool.run(call.input, ToolContext(cwd=self.cwd, memory_dir=".memory"))
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = f"Tool not found: {call.tool_name}"

                self.history.append(ChatMessage(
                    id=make_id(), role="tool", name=call.tool_name,
                    content=result[:6000], timestamp=now,
                ))
                all_tool_calls.append(call)
                self.total_tools += 1

        fallback = "(max rounds reached)"
        self.history.append(ChatMessage(id=make_id(), role="assistant", content=fallback, timestamp=now))
        return {"response": fallback, "tool_calls": all_tool_calls, "tools_used": [tc.tool_name for tc in all_tool_calls]}


def _banner(models: list[str], project: str):
    console.print()
    console.print(f"  [{CYAN}]{'━' * 60}[/]")
    console.print(f"  [{CYAN}]  ╔══════════════════════════════════════════════════╗[/]")
    console.print(f"  [{CYAN}]  ║[/]  [bold {CYAN}]F O R G E   T E A M[/]   [{DIM}]Unified Agent Terminal[/]  [{CYAN}]║[/]")
    console.print(f"  [{CYAN}]  ╚══════════════════════════════════════════════════╝[/]")
    console.print(f"  [{CYAN}]{'━' * 60}[/]")
    console.print()
    console.print(f"  [{DIM}]Project:[/]  {project}")
    console.print(f"  [{DIM}]Agents:[/]   {len(models)}")
    for i, m in enumerate(models):
        c = AGENT_COLORS[i % len(AGENT_COLORS)]
        console.print(f"    [{c}]{AGENT_ICONS[i]}[/]  {m}")
    console.print()
    console.print(f"  [{DIM}]All agents receive your prompt. They see each other's work.[/]")
    console.print(f"  [{DIM}]Commands: /status /clear /exit[/]")
    console.print()


def _show_agent_response(slot: AgentSlot, result: dict):
    """Show one agent's response with its color and label."""
    response = result["response"]
    tools_used = result.get("tools_used", [])

    header = f"[bold {slot.color}]{slot.icon}[/] [{DIM}]{slot.model}[/]"
    if tools_used:
        header += f"  [{DIM}]tools: {', '.join(tools_used)}[/]"

    # Truncate very long responses for display
    display = response[:1500]
    if len(response) > 1500:
        display += f"\n[{DIM}]...({len(response)} chars total)[/]"

    if "```" in display:
        try:
            console.print(Panel(
                Markdown(display),
                title=header,
                border_style=slot.color,
                box=box.ROUNDED,
                padding=(0, 1),
            ))
        except Exception:
            console.print(Panel(display, title=header, border_style=slot.color, box=box.ROUNDED, padding=(0, 1)))
    else:
        console.print(Panel(
            display,
            title=header,
            border_style=slot.color,
            box=box.ROUNDED,
            padding=(0, 1),
        ))


async def start_team_cli(models: list[str], project_path: str = ".",
                          ollama_url: str = "http://127.0.0.1:11434") -> None:
    """Run the unified multi-agent terminal."""
    import os
    cwd = os.path.abspath(project_path)
    client = OllamaClient(ollama_url)
    tools = create_tool_registry()

    # Check Ollama
    alive = await client.ping()
    if not alive:
        console.print(f"  [{RED}]Cannot reach Ollama at {ollama_url}[/]")
        return

    _banner(models, cwd)

    # Build system prompt
    system = (
        "You are part of a coding agent team. You MUST use tools to complete tasks. "
        "NEVER just describe what to do — use write_file, edit_file, bash, read_file tools. "
        "When another agent has already done part of the work, build on it — don't redo it. "
        "Coordinate: if you see another agent created a file, read it and extend it. "
        "Always respond with tool calls in ```tool blocks."
    )

    # Read AGENT.md for context
    from pathlib import Path
    agent_md = Path(cwd) / ".forgeagent" / "AGENT.md"
    if agent_md.exists():
        system += "\n\n## Project Instructions\n" + agent_md.read_text(encoding="utf-8")[:3000]

    # Create agent slots
    agents = []
    for i, model in enumerate(models[:6]):
        slot = AgentSlot(i, model, client, tools, cwd, system)
        agents.append(slot)
        console.print(f"  [{AGENT_COLORS[i]}]{AGENT_ICONS[i]} {model} ready[/]")

    console.print()
    session_start = time.time()

    while True:
        try:
            elapsed = int(time.time() - session_start) // 60
            total_tools = sum(a.total_tools for a in agents)
            console.print(f"  [{DIM}]{len(agents)} agents | {total_tools} tools | {elapsed}m[/]", end="  ")
            prompt = console.input(f"[bold {CYAN}]> [/]")
        except (EOFError, KeyboardInterrupt):
            break

        if not prompt.strip():
            continue

        # Commands
        if prompt.strip() == "/exit":
            break
        if prompt.strip() == "/clear":
            console.clear()
            _banner([a.model for a in agents], cwd)
            continue
        if prompt.strip() == "/status":
            for a in agents:
                console.print(f"  [{a.color}]{a.icon}[/]  {a.model}  [{DIM}]{len(a.history)} msgs, {a.total_tools} tools[/]")
            console.print()
            continue

        console.print()
        console.print(Rule(style=DIM))

        # Send to all agents — each sees previous agents' responses as context
        shared_context = ""
        for agent in agents:
            console.print(f"  [{agent.color}]{agent.icon} {agent.model} thinking...[/]")

            result = await agent.send(prompt, shared_context)
            _show_agent_response(agent, result)

            # Build shared context for next agent
            response_summary = result["response"][:500]
            tools_summary = ""
            if result.get("tools_used"):
                tools_summary = f" (used tools: {', '.join(result['tools_used'])})"
            shared_context += f"\n[{agent.icon} {agent.model}]{tools_summary}: {response_summary}\n"

        console.print()

    console.print(f"\n  [{CYAN}]Team session ended.[/]")
