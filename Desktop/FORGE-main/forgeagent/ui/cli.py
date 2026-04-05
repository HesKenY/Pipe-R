"""Plain-text REPL interface (--cli mode)."""
from __future__ import annotations
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


async def start_cli(ctx) -> None:
    """Run the plain REPL loop."""
    from ..commands.registry import create_commands
    from ..core.interfaces import CommandContext

    commands = ctx["commands"]
    engine = ctx["engine"]
    config = ctx["config"]
    buddy = ctx["buddy"]
    memory = ctx["memory"]
    session_store = ctx["session_store"]

    # Banner
    console.print(Panel.fit(
        "[bold cyan]ForgeAgent[/] — Local AI Coding Agent Hub\n"
        "[dim]Ollama-powered · 100% Offline · Persistent Memory[/]",
        border_style="cyan",
    ))

    # Health check
    alive = await engine.client.ping()
    if not alive:
        console.print(f"[red]Cannot reach Ollama at {config.ollama_base_url}[/]")
        console.print("[dim]Make sure Ollama is running: ollama serve[/]")

    # Auto-restore
    last = await session_store.load_latest()
    if last and len(last) > 2:
        engine.restore_messages(last)
        console.print(f"[green]Restored session ({len(last)} messages)[/]")

    # Status
    agents = ctx["deployer"].list_agents()
    datasets = ctx["dataset_manager"].list_datasets()
    console.print(f"[dim]Model: {config.model} | Agents: {len(agents)} | Datasets: {len(datasets)} | {buddy.summary.name} Lv.{buddy.summary.level}[/]")
    console.print(f"[dim]{buddy.get_quip()}[/]")
    console.print("[dim]Type /help for commands · /hub for dashboard[/]\n")

    turn_count = 0

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
            prompt = console.input("[bold cyan]  You > [/]")
        except (EOFError, KeyboardInterrupt):
            break

        if not prompt.strip():
            continue

        # Slash commands
        if prompt.startswith("/"):
            parts = prompt[1:].split(" ", 1)
            cmd_name = parts[0]
            cmd_input = parts[1] if len(parts) > 1 else ""
            cmd = commands.get(cmd_name)
            if not cmd:
                console.print(f"[yellow]Unknown command: /{cmd_name}[/]")
                continue
            try:
                result = await cmd.run(cmd_input, make_ctx())
                if result.output:
                    console.print(f"[yellow]{result.output}[/]")
                if result.should_exit:
                    break
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
            continue

        # @N slot shorthand
        import re
        slot_match = re.match(r"^@(\d)\s+(.+)", prompt)
        if slot_match:
            slot, msg = int(slot_match.group(1)), slot_match.group(2)
            if 1 <= slot <= 6:
                console.print(f"[dim]Sending to slot {slot}...[/]")
                try:
                    resp = await ctx["instance_manager"].send_to_slot(slot, msg)
                    console.print(Panel(resp[:2000], title=f"Slot {slot}", border_style="green"))
                except Exception as e:
                    console.print(f"[red]Slot {slot}: {e}[/]")
                continue

        # Normal query
        turn_count += 1
        buddy.on_interaction()
        try:
            def on_stream(chunk):
                console.print(chunk, end="")

            result = await engine.submit_user_message(prompt, on_stream=on_stream)
            console.print()  # newline after stream

            if result.tool_calls:
                for tc in result.tool_calls:
                    console.print(f"[magenta]  > {tc.tool_name}[/] [dim]{str(tc.input)[:60]}[/]")
                    buddy.on_tool_use()

            if not result.tool_calls:
                console.print(f"\n[bold green]ForgeAgent >[/] {result.assistant_message.content}\n")

            # Auto-dream
            if turn_count > 0 and turn_count % config.dream_interval == 0:
                console.print("[yellow]Auto-dreaming...[/]")
                await memory.dream(engine.summarize, engine.get_messages())
                buddy.on_dream()
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
