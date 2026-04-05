"""Plain-text REPL interface (--cli mode) and Agent CLI mode (--agent)."""
from __future__ import annotations
import asyncio
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich import box

console = Console()

# ══════════════════════════════════════════════════════════════
#  SCI-FI THEME CONSTANTS
# ══════════════════════════════════════════════════════════════
CYAN = "#00e5ff"
PURPLE = "#7c4dff"
GREEN = "#00e676"
RED = "#ff1744"
AMBER = "#ffd740"
DIM = "#5c6b7a"
SURFACE = "#111822"


# ══════════════════════════════════════════════════════════════
#  AGENT CLI — Rich terminal coding agent
# ══════════════════════════════════════════════════════════════
def _agent_banner(agent_name: str, model: str, project: str, tools: list[str]):
    """Print the sci-fi agent startup banner."""
    console.print()
    console.print(f"  [{CYAN}]{'━' * 58}[/]")
    console.print(f"  [{CYAN}]  ╔═══════════════════════════════════════════════════╗[/]")
    console.print(f"  [{CYAN}]  ║[/]  [bold {CYAN}]F O R G E   A G E N T[/]  [{DIM}]Terminal Coding Agent[/]  [{CYAN}]║[/]")
    console.print(f"  [{CYAN}]  ╚═══════════════════════════════════════════════════╝[/]")
    console.print(f"  [{CYAN}]{'━' * 58}[/]")
    console.print()

    info = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    info.add_column(style=f"{DIM}", width=12)
    info.add_column(style="bold white")
    info.add_row("AGENT", agent_name)
    info.add_row("MODEL", f"[{CYAN}]{model}[/]")
    info.add_row("PROJECT", project)
    info.add_row("TOOLS", f"[{DIM}]{len(tools)} available[/]")
    console.print(info)
    console.print()
    console.print(f"  [{DIM}]Type a task and press Enter. The agent will use tools to complete it.[/]")
    console.print(f"  [{DIM}]Commands: /help /status /tools /compact /save /clear /exit[/]")
    console.print()


def _show_tool_call(tool_name: str, tool_input: dict):
    """Display a tool call with sci-fi styling."""
    # Format the input nicely
    input_lines = []
    for k, v in tool_input.items():
        val = str(v)
        if len(val) > 80:
            val = val[:77] + "..."
        input_lines.append(f"  [{DIM}]{k}:[/] {val}")
    input_text = "\n".join(input_lines) if input_lines else f"  [{DIM}](no args)[/]"

    panel = Panel(
        input_text,
        title=f"[bold {PURPLE}]{tool_name}[/]",
        border_style=PURPLE,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def _show_tool_result(tool_name: str, result: str):
    """Display a tool result with appropriate formatting."""
    # Detect content type and format accordingly
    if tool_name == "bash":
        # Show bash output in a dimmed panel
        lines = result.split("\n")
        # Show first line (exit code) separately
        if lines and lines[0].startswith("Exit "):
            exit_line = lines[0]
            output = "\n".join(lines[1:])[:2000]
            exit_code = exit_line.split()[1] if len(exit_line.split()) > 1 else "?"
            color = GREEN if exit_code == "0" else RED
            console.print(f"  [{color}]{exit_line}[/]")
            if output.strip():
                console.print(Panel(
                    output[:2000],
                    border_style=DIM,
                    box=box.SIMPLE,
                    padding=(0, 1),
                ))
        else:
            console.print(Panel(result[:2000], border_style=DIM, box=box.SIMPLE))

    elif tool_name in ("read_file", "search_files"):
        # Show file content with line numbers preserved
        lines = result.split("\n")
        header = lines[0] if lines else ""
        content = "\n".join(lines[1:])[:2000]
        console.print(f"  [{DIM}]{header}[/]")
        if content.strip():
            # Try to detect language from file extension
            ext = ""
            for word in header.split():
                if "." in word:
                    ext = word.rsplit(".", 1)[-1].split(")")[0].split(" ")[0]
                    break
            lang_map = {"py": "python", "js": "javascript", "ts": "typescript",
                        "rs": "rust", "go": "go", "java": "java", "json": "json",
                        "yaml": "yaml", "yml": "yaml", "md": "markdown", "toml": "toml",
                        "html": "html", "css": "css", "sh": "bash", "bat": "batch"}
            lang = lang_map.get(ext, "")
            if lang:
                try:
                    console.print(Syntax(content[:2000], lang, theme="monokai",
                                         line_numbers=False, padding=(0, 1)))
                except Exception:
                    console.print(Panel(content[:2000], border_style=DIM, box=box.SIMPLE))
            else:
                console.print(Panel(content[:2000], border_style=DIM, box=box.SIMPLE))

    elif tool_name in ("write_file", "edit_file"):
        # Show write/edit confirmation
        console.print(f"  [{GREEN}]{result}[/]")

    elif tool_name == "list_dir":
        # Show directory listing
        console.print(Panel(result[:2000], title=f"[{DIM}]files[/]",
                            border_style=DIM, box=box.SIMPLE, padding=(0, 1)))

    else:
        # Generic result
        if len(result) > 200:
            console.print(Panel(result[:2000], border_style=DIM, box=box.SIMPLE, padding=(0, 1)))
        else:
            console.print(f"  [{DIM}]{result}[/]")


def _show_response(text: str):
    """Render assistant response with markdown."""
    console.print()
    # Check if response contains code blocks — use Markdown rendering
    if "```" in text:
        try:
            console.print(Panel(
                Markdown(text),
                title=f"[bold {GREEN}]ForgeAgent[/]",
                border_style=GREEN,
                box=box.ROUNDED,
                padding=(1, 2),
            ))
        except Exception:
            console.print(Panel(text, title=f"[bold {GREEN}]ForgeAgent[/]",
                                border_style=GREEN, box=box.ROUNDED, padding=(1, 2)))
    else:
        console.print(Panel(
            text,
            title=f"[bold {GREEN}]ForgeAgent[/]",
            border_style=GREEN,
            box=box.ROUNDED,
            padding=(1, 2),
        ))
    console.print()


async def start_agent_cli(ctx: dict, agent_config: dict | None = None) -> None:
    """Run the agent CLI — a rich terminal coding agent experience."""
    from ..commands.registry import create_commands
    from ..core.interfaces import CommandContext

    commands = ctx["commands"]
    engine = ctx["engine"]
    config = ctx["config"]
    buddy = ctx["buddy"]
    memory = ctx["memory"]
    session_store = ctx["session_store"]

    # Agent-specific overrides
    agent_name = "ForgeAgent"
    if agent_config:
        agent_name = agent_config.get("name", "ForgeAgent")
        if agent_config.get("modelName"):
            engine.set_model(agent_config["modelName"])
            config.model = agent_config["modelName"]
        if agent_config.get("systemPrompt"):
            config.system_prompt = agent_config["systemPrompt"]

    # Get tool names
    tool_names = list(engine.tools.keys())

    # Banner
    _agent_banner(agent_name, config.model, config.cwd, tool_names)

    # Health check
    alive = await engine.client.ping()
    if alive:
        console.print(f"  [{GREEN}]Connected to Ollama[/]")
    else:
        console.print(f"  [{RED}]Cannot reach Ollama at {config.ollama_base_url}[/]")
        console.print(f"  [{DIM}]Start Ollama: ollama serve[/]")
    console.print()

    # Auto-restore session
    last = await session_store.load_latest()
    if last and len(last) > 2:
        engine.restore_messages(last)
        console.print(f"  [{DIM}]Session restored ({len(last)} messages)[/]")

    turn_count = 0
    session_start = time.time()
    total_tools = 0

    def make_ctx():
        return CommandContext(
            config=config, engine=engine, buddy=buddy, memory=memory,
            session_store=session_store, deployer=ctx["deployer"],
            dataset_manager=ctx["dataset_manager"], model_builder=ctx["model_builder"],
            evaluator=ctx["evaluator"], scraper=ctx["scraper"],
            instance_manager=ctx["instance_manager"],
        )

    while True:
        try:
            # Status line before prompt
            elapsed = int(time.time() - session_start)
            mins = elapsed // 60
            console.print(
                f"  [{DIM}]{config.model} | {total_tools} tools | {mins}m[/]",
                end="  ",
            )
            prompt = console.input(f"[bold {CYAN}]> [/]")
        except (EOFError, KeyboardInterrupt):
            break

        if not prompt.strip():
            continue

        # Slash commands
        if prompt.startswith("/"):
            parts = prompt[1:].split(" ", 1)
            cmd_name = parts[0]
            cmd_input = parts[1] if len(parts) > 1 else ""

            if cmd_name == "tools":
                console.print(f"\n  [bold]Available Tools ({len(tool_names)}):[/]")
                for name in sorted(tool_names):
                    tool = engine.tools.get(name)
                    desc = tool.definition.description if tool else ""
                    console.print(f"  [{CYAN}]{name:<16}[/] [{DIM}]{desc}[/]")
                console.print()
                continue

            cmd = commands.get(cmd_name)
            if not cmd:
                console.print(f"  [{AMBER}]Unknown: /{cmd_name}[/]")
                continue
            try:
                result = await cmd.run(cmd_input, make_ctx())
                if result.output:
                    console.print(Panel(result.output, border_style=DIM, box=box.ROUNDED, padding=(0, 1)))
                if result.should_exit:
                    break
            except Exception as e:
                console.print(f"  [{RED}]Error: {e}[/]")
            continue

        # @N slot shorthand
        import re
        slot_match = re.match(r"^@(\d)\s+(.+)", prompt)
        if slot_match:
            slot, msg = int(slot_match.group(1)), slot_match.group(2)
            if 1 <= slot <= 6:
                with console.status(f"[{PURPLE}]Sending to slot {slot}...[/]"):
                    try:
                        resp = await ctx["instance_manager"].send_to_slot(slot, msg)
                        console.print(Panel(resp[:2000], title=f"Slot {slot}", border_style=PURPLE, box=box.ROUNDED))
                    except Exception as e:
                        console.print(f"  [{RED}]Slot {slot}: {e}[/]")
                continue

        # ── Normal query — the agent does its work ────
        turn_count += 1
        buddy.on_interaction()
        console.print()
        console.print(Rule(style=DIM))

        try:
            # Show thinking indicator
            with console.status(f"[{CYAN}]Thinking...[/]", spinner="dots"):
                result = await engine.submit_user_message(
                    prompt,
                    on_tool=lambda name, inp: None,  # we show tools from result
                )

            # Show tool calls
            if result.tool_calls:
                console.print(f"  [{DIM}]Used {len(result.tool_calls)} tool(s)[/]")
                for tc in result.tool_calls:
                    _show_tool_call(tc.tool_name, tc.input)
                    buddy.on_tool_use()
                    total_tools += 1

                # Show tool results from messages
                for msg in engine.get_messages():
                    if msg.role == "tool" and msg.name:
                        # Find matching tool call
                        for tc in result.tool_calls:
                            if tc.tool_name == msg.name:
                                _show_tool_result(msg.name, msg.content)
                                break

            # Show response
            _show_response(result.assistant_message.content)

            # Auto-dream
            if turn_count > 0 and turn_count % config.dream_interval == 0:
                console.print(f"  [{AMBER}]Consolidating memory...[/]")
                await memory.dream(engine.summarize, engine.get_messages())
                buddy.on_dream()

        except Exception as e:
            console.print(f"  [{RED}]Error: {e}[/]")

    # Goodbye
    console.print()
    console.print(f"  [{CYAN}]Session saved. Goodbye.[/]")
    await engine.save_session()


# ══════════════════════════════════════════════════════════════
#  BASIC CLI — legacy plain REPL (--cli flag)
# ══════════════════════════════════════════════════════════════
async def start_cli(ctx) -> None:
    """Run the plain REPL loop (legacy mode)."""
    # Redirect to agent CLI — it's strictly better
    await start_agent_cli(ctx)
