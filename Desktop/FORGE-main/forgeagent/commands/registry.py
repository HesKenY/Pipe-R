"""All slash commands for ForgeAgent."""
from __future__ import annotations
from ..core.interfaces import Command, CommandContext, CommandResult


class HelpCommand(Command):
    name = "help"
    description = "Show available commands"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        sections = [
            ("General", [
                ("help", "Show this list"),
                ("hub", "Dashboard overview"),
                ("model <name>", "Switch or show current model"),
                ("status", "Runtime info"),
            ]),
            ("Training", [
                ("dataset <sub>", "create | list | generate | harvest | harvest-code | export | delete | add"),
                ("scrape <sub>", "topics | topic <ds> <t> | url <ds> <url> | github <ds> <url>"),
                ("train <sub>", "list | create <n> <base> | build <n> | models | pull <m> | bases | delete <n>"),
                ("eval <sub>", "run [model] | smoke [model] | reports"),
            ]),
            ("Deploy", [
                ("deploy <n> <path>", "Deploy agent to project folder"),
                ("agents", "List deployed agents"),
                ("launch <n>", "Open agent in new terminal"),
                ("undeploy <n>", "Remove deployed agent"),
                ("templates", "Show 8 agent presets"),
                ("slots <sub>", "show | load | unload | send | broadcast | coordinate | crossref"),
            ]),
            ("Session", [
                ("tasks", "View task list"),
                ("buddy", "Companion status"),
                ("memory", "Memory stats"),
                ("dream", "Force memory consolidation"),
                ("compact", "Compress conversation context"),
                ("save", "Save session"),
                ("clear", "Clear conversation"),
                ("exit", "Save and quit"),
            ]),
        ]
        lines = ["[bold]Commands[/]", ""]
        for title, cmds in sections:
            lines.append(f"  [bold yellow]{title}[/]")
            for name, desc in cmds:
                lines.append(f"    [cyan]/{name:<24}[/] {desc}")
            lines.append("")
        lines.append("  [dim]Ctrl+S save | Ctrl+L clear log | @1-@6 msg to slot[/]")
        return CommandResult(output="\n".join(lines))


class ModelCommand(Command):
    name = "model"
    aliases = ["m"]
    description = "Switch or show model"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        if not inp.strip():
            return CommandResult(output=f"Model: [cyan]{ctx.config.model}[/]")
        ctx.engine.set_model(inp.strip())
        return CommandResult(output=f"Model set to [cyan]{inp.strip()}[/]")


class ClearCommand(Command):
    name = "clear"
    description = "Clear conversation"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        await ctx.engine.save_session()
        ctx.engine.clear_messages()
        return CommandResult(output="Cleared. Previous session saved.")


class SaveCommand(Command):
    name = "save"
    description = "Save session"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        sid = await ctx.engine.save_session()
        return CommandResult(output=f"Saved: {sid}")


class CompactCommand(Command):
    name = "compact"
    description = "Compact context"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        return CommandResult(output=await ctx.engine.compact())


class StatusCommand(Command):
    name = "status"
    description = "Runtime status"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        s = ctx.memory.stats()
        b = ctx.buddy.summary
        agents = ctx.deployer.list_agents()
        msgs = len(ctx.engine.get_messages())
        lines = [
            "[bold]Status[/]", "",
            f"  Model       [cyan]{ctx.config.model}[/]",
            f"  Messages    {msgs}",
            f"  Memory      {s['size_kb']} KB  ({s['dreams']} dreams)",
            f"  Buddy       {b.name} Lv.{b.level} ({b.mood})",
            f"  Agents      {len(agents)}",
            f"  CWD         [dim]{ctx.config.cwd}[/]",
        ]
        return CommandResult(output="\n".join(lines))


class ExitCommand(Command):
    name = "exit"
    aliases = ["quit", "q"]
    description = "Save and quit"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        await ctx.engine.save_session()
        return CommandResult(output="Session saved. Goodbye!", should_exit=True)


class TasksCommand(Command):
    name = "tasks"
    description = "Show tasks"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        tool = ctx.engine.tools.get("task")
        if not tool:
            return CommandResult(output="Task tool not available.")
        from ..core.interfaces import ToolContext
        result = await tool.run({"action": "list"}, ToolContext(cwd=ctx.config.cwd, memory_dir=ctx.config.memory_dir))
        return CommandResult(output=result)


class BuddyCommand(Command):
    name = "buddy"
    description = "Show buddy"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        b = ctx.buddy.summary
        pct = min(100, int(b.xp / max(1, b.xp_to_next) * 100))
        bar = "[green]" + "#" * (pct // 5) + "[/][dim]" + "-" * (20 - pct // 5) + "[/]"
        lines = [
            f"[bold]{b.name}[/]  Level {b.level}  ({b.mood})",
            f"  XP    [{bar}] {b.xp}/{b.xp_to_next}",
            f"  Energy  {b.energy}%",
            f"  [dim italic]{ctx.buddy.get_quip()}[/]",
        ]
        return CommandResult(output="\n".join(lines))


class MemoryCommand(Command):
    name = "memory"
    aliases = ["mem"]
    description = "Memory stats"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        s = ctx.memory.stats()
        return CommandResult(output=f"Memory: {s['size_kb']} KB  |  Dreams: {s['dreams']}  |  Last: {s['last_dream'] or 'none'}")


class DreamCommand(Command):
    name = "dream"
    description = "Force memory consolidation"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        await ctx.memory.dream(ctx.engine.summarize, ctx.engine.get_messages())
        ctx.buddy.on_dream()
        return CommandResult(output="Dream complete. Memory consolidated.")


class HubCommand(Command):
    name = "hub"
    description = "Dashboard overview"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        models = ctx.model_builder.list_local_models()
        profiles = ctx.model_builder.list_profiles()
        datasets = ctx.dataset_manager.list_datasets()
        agents = ctx.deployer.list_agents()
        total_ex = sum(d.get("exampleCount", 0) for d in datasets)
        active_slots = ctx.instance_manager.get_active_slots()
        b = ctx.buddy.summary
        lines = [
            "[bold]ForgeAgent Hub[/]", "",
            f"  [cyan]Model[/]     {ctx.config.model}",
            f"  [cyan]Ollama[/]    {len(models)} models installed",
            f"  [cyan]Profiles[/]  {len(profiles)}",
            f"  [cyan]Datasets[/]  {len(datasets)} ({total_ex} examples)",
            f"  [cyan]Agents[/]    {len(agents)} deployed",
            f"  [cyan]Slots[/]     {len(active_slots)}/6 active",
            f"  [cyan]Buddy[/]     {b.name} Lv.{b.level}",
        ]
        return CommandResult(output="\n".join(lines))


class DatasetCommand(Command):
    name = "dataset"
    aliases = ["ds"]
    description = "Manage datasets"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "list"
        dm = ctx.dataset_manager
        if sub == "list":
            ds = dm.list_datasets()
            if not ds:
                return CommandResult(output="No datasets. Create one: /dataset create <name>")
            lines = ["[bold]Datasets[/]", ""]
            for d in ds:
                tags = ", ".join(d.get("tags", []))
                lines.append(f"  {d['name']:<20} {d.get('exampleCount', 0):>4} examples  [dim]{tags}[/]")
            return CommandResult(output="\n".join(lines))
        elif sub == "create":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /dataset create <name> [description]")
            dm.create_dataset(name, " ".join(args[2:]))
            return CommandResult(output=f"Dataset [cyan]{name}[/] created.")
        elif sub == "generate":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /dataset generate <name> [count]")
            count = int(args[2]) if len(args) > 2 else 20
            n = dm.generate_tool_use_examples(name, count)
            return CommandResult(output=f"Generated {n} examples into [cyan]{name}[/].")
        elif sub == "harvest":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /dataset harvest <name>")
            n = dm.harvest_from_conversation(name, ctx.engine.get_messages())
            return CommandResult(output=f"Harvested {n} examples from conversation.")
        elif sub in ("harvest-code", "harvestcode"):
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /dataset harvest-code <name> [path]")
            path = args[2] if len(args) > 2 else ctx.config.cwd
            n = dm.harvest_from_codebase(name, path)
            return CommandResult(output=f"Harvested {n} examples from codebase.")
        elif sub == "export":
            name = args[1] if len(args) > 1 else None
            fmt = args[2] if len(args) > 2 else "jsonl"
            if not name:
                return CommandResult(output="Usage: /dataset export <name> [jsonl|chatml|alpaca|openai]")
            path = dm.export_dataset(name, fmt)
            return CommandResult(output=f"Exported -> {path}")
        elif sub == "delete":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /dataset delete <name>")
            ok = dm.delete_dataset(name)
            return CommandResult(output=f"Deleted." if ok else "Not found.")
        elif sub == "add":
            name = args[1] if len(args) > 1 else None
            rest = " ".join(args[2:])
            if not name or "|" not in rest:
                return CommandResult(output="Usage: /dataset add <name> <prompt> | <completion>")
            p, c = rest.split("|", 1)
            dm.add_manual_example(name, p.strip(), c.strip())
            return CommandResult(output=f"Added example to [cyan]{name}[/].")
        return CommandResult(output="Sub: list, create, generate, harvest, harvest-code, export, delete, add")


class TrainCommand(Command):
    name = "train"
    description = "Build/train models"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "list"
        mb = ctx.model_builder
        if sub == "list":
            profiles = mb.list_profiles()
            if not profiles:
                return CommandResult(output="No profiles. Create: /train create <name> <base_model>")
            lines = ["[bold]Training Profiles[/]", ""]
            for p in profiles:
                icon = "[green]V[/]" if p.get("built") else "[yellow]O[/]"
                lines.append(f"  {icon} {p['name']:<20} {p['baseModel']:<25} {p.get('datasetName', '')}")
            return CommandResult(output="\n".join(lines))
        elif sub == "create":
            name, base = (args[1] if len(args) > 1 else None), (args[2] if len(args) > 2 else None)
            if not name or not base:
                return CommandResult(output="Usage: /train create <name> <base_model> [dataset]")
            ds = args[3] if len(args) > 3 else None
            mb.create_profile(name, base, dataset_name=ds)
            return CommandResult(output=f"Profile [cyan]{name}[/] created.")
        elif sub == "build":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /train build <name>")
            result = await mb.build_model(name, ctx.dataset_manager)
            status = "[green]OK[/]" if result.success else "[red]FAIL[/]"
            return CommandResult(output=f"{status}: {result.message}")
        elif sub == "models":
            models = mb.list_local_models()
            if not models:
                return CommandResult(output="No local models.")
            lines = ["[bold]Ollama Models[/]", ""]
            for m in models:
                lines.append(f"  {m['name']:<30} {m['size']:<10} {m['modified']}")
            return CommandResult(output="\n".join(lines))
        elif sub == "pull":
            model = args[1] if len(args) > 1 else None
            if not model:
                return CommandResult(output="Usage: /train pull <model>")
            r = await mb.pull_base_model(model)
            return CommandResult(output=r["message"])
        elif sub == "bases":
            lines = ["[bold]Recommended Bases[/]", ""]
            for b in mb.get_recommended_bases():
                lines.append(f"  {b['name']:<30} {b['size']:<6} {b['family']}")
            return CommandResult(output="\n".join(lines))
        elif sub == "delete":
            name = args[1] if len(args) > 1 else None
            if not name:
                return CommandResult(output="Usage: /train delete <name>")
            mb.delete_profile(name)
            r = mb.delete_model(name)
            return CommandResult(output=r["message"])
        return CommandResult(output="Sub: list, create, build, models, pull, bases, delete")


class EvalCommand(Command):
    name = "eval"
    aliases = ["evaluate"]
    description = "Evaluate models"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "help"
        ev = ctx.evaluator
        if sub == "run":
            model = args[1] if len(args) > 1 else ctx.config.model
            report = await ev.evaluate(model)
            lines = [
                f"[bold]Eval: {report['modelName']}[/]", "",
                f"  Score     [cyan]{report['avgScore']}%[/]",
                f"  Passed    {report['passed']}/{report['totalCases']}",
                f"  Latency   {report['avgLatencyMs']}ms avg",
            ]
            for cat, s in report.get("byCategory", {}).items():
                lines.append(f"  {cat:<20} {s['passed']}/{s['total']} ({s['score']}%)")
            return CommandResult(output="\n".join(lines))
        elif sub == "smoke":
            model = args[1] if len(args) > 1 else ctx.config.model
            r = await ev.smoke_test(model)
            alive = "[green]yes[/]" if r["alive"] else "[red]no[/]"
            chat = "[green]yes[/]" if r["canChat"] else "[red]no[/]"
            tool = "[green]yes[/]" if r["canTool"] else "[red]no[/]"
            return CommandResult(output=f"Alive: {alive}  Chat: {chat}  Tools: {tool}  Latency: {r['latencyMs']}ms")
        elif sub == "reports":
            reports = ev.list_reports()
            if not reports:
                return CommandResult(output="No eval reports yet.")
            lines = ["[bold]Eval Reports[/]", ""]
            for r in reports:
                lines.append(f"  {r['model']:<20} {r['date'][:16]:<18} score: {r['score']}%")
            return CommandResult(output="\n".join(lines))
        return CommandResult(output="Sub: run [model], smoke [model], reports")


class DeployCommand(Command):
    name = "deploy"
    description = "Deploy agent to project"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        if len(args) < 2:
            from ..deploy.templates import list_templates
            tpls = ", ".join(t["id"] for t in list_templates())
            return CommandResult(output=f"Usage: /deploy <name> <project_path> [model] [template]\nTemplates: {tpls}")
        name, path = args[0], args[1]
        model = args[2] if len(args) > 2 else ctx.config.model
        tpl = args[3] if len(args) > 3 else None
        agent = ctx.deployer.deploy(name, path, model, tpl)
        return CommandResult(output=f"Deployed [cyan]{agent['name']}[/] -> {agent['projectPath']}\nLaunch: /launch {agent['name']}")


class AgentsCommand(Command):
    name = "agents"
    description = "List deployed agents"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "list"
        if sub == "info" and len(args) > 1:
            info = ctx.deployer.get_agent_info(args[1])
            if not info:
                return CommandResult(output="Agent not found.")
            a = info["agent"]
            lines = [
                f"[bold]{a['name']}[/]", "",
                f"  Model    {a['modelName']}",
                f"  Path     {a['projectPath']}",
                f"  Status   {a.get('status', 'idle')}",
                f"  Memory   {info['memorySize']}B",
                f"  Sessions {info['sessionCount']}",
            ]
            return CommandResult(output="\n".join(lines))
        agents = ctx.deployer.list_agents()
        if not agents:
            return CommandResult(output="No agents deployed. Use /deploy or click EASY DEPLOY.")
        lines = ["[bold]Agents[/]", ""]
        for a in agents:
            icon = "[green]*[/]" if a.get("status") == "running" else "[dim]o[/]"
            lines.append(f"  {icon} {a['name']:<16} {a['modelName']:<24} [dim]{a['projectPath'][-40:]}[/]")
        return CommandResult(output="\n".join(lines))


class LaunchCommand(Command):
    name = "launch"
    description = "Launch agent in new terminal"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        name = inp.strip()
        if not name:
            return CommandResult(output="Usage: /launch <agent_name>")
        r = ctx.deployer.launch(name)
        return CommandResult(output=r["message"])


class UndeployCommand(Command):
    name = "undeploy"
    description = "Remove agent"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        if not args:
            return CommandResult(output="Usage: /undeploy <name> [--remove-files]")
        ok = ctx.deployer.undeploy(args[0], "--remove-files" in args)
        return CommandResult(output="Removed." if ok else "Not found.")


class TemplatesCommand(Command):
    name = "templates"
    aliases = ["tpl"]
    description = "List agent templates"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        from ..deploy.templates import list_templates
        lines = ["[bold]Templates[/]", ""]
        for t in list_templates():
            lines.append(f"  [cyan]{t['id']:<14}[/] {t['name']:<22} [dim]{t['description']}[/]")
        return CommandResult(output="\n".join(lines))


class SlotsCommand(Command):
    name = "slots"
    description = "Manage 6 model slots"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "show"
        im = ctx.instance_manager
        if sub in ("show", ""):
            lines = ["[bold]Model Slots[/]", ""]
            for s in im.get_all_slots():
                if s["status"] == "busy": icon = "[yellow]*[/]"
                elif s["status"] == "loaded": icon = "[green]o[/]"
                else: icon = "[dim].[/]"
                model = s["modelName"] or "[dim](empty)[/]"
                lines.append(f"  {icon} Slot {s['slot']}  {model:<24} {s['messagesCount']} msgs")
            return CommandResult(output="\n".join(lines))
        elif sub == "load":
            slot = int(args[1]) if len(args) > 1 else 0
            model = args[2] if len(args) > 2 else None
            if not slot or not model:
                return CommandResult(output="Usage: /slots load <1-6> <model>")
            im.load_model(slot, model)
            return CommandResult(output=f"Slot {slot} loaded with [cyan]{model}[/].")
        elif sub == "unload":
            slot = int(args[1]) if len(args) > 1 else 0
            im.unload_model(slot)
            return CommandResult(output=f"Slot {slot} unloaded.")
        elif sub == "send":
            slot = int(args[1]) if len(args) > 1 else 0
            msg = " ".join(args[2:])
            if not slot or not msg:
                return CommandResult(output="Usage: /slots send <1-6> <message>")
            resp = await im.send_to_slot(slot, msg)
            return CommandResult(output=f"[green]Slot {slot}:[/] {resp[:2000]}")
        elif sub == "broadcast":
            msg = " ".join(args[1:])
            if not msg:
                return CommandResult(output="Usage: /slots broadcast <message>")
            results = await im.broadcast(msg)
            lines = [f"[green]Slot {s}:[/] {r[:500]}" for s, r in results.items()]
            return CommandResult(output="\n\n".join(lines))
        elif sub == "coordinate":
            task = " ".join(args[1:])
            if not task:
                return CommandResult(output="Usage: /slots coordinate <task>")
            results = await im.coordinate_work(task)
            lines = [f"[green]Slot {s}:[/] {r[:500]}" for s, r in results.items()]
            return CommandResult(output="\n\n".join(lines))
        elif sub == "crossref":
            result = await im.cross_reference()
            if result["conflicts"]:
                lines = ["[bold yellow]Conflicts found:[/]"]
                for c in result["conflicts"]:
                    lines.append(f"  Slot {c['slot1']} <> Slot {c['slot2']}: {c['file']}")
                return CommandResult(output="\n".join(lines))
            return CommandResult(output="[green]No conflicts detected.[/]")
        elif sub == "clear":
            slot = int(args[1]) if len(args) > 1 else 0
            im.clear_slot_history(slot)
            return CommandResult(output=f"Slot {slot} cleared.")
        elif sub == "history":
            slot = int(args[1]) if len(args) > 1 else 0
            history = im.get_slot_history(slot)
            lines = [f"  [{m.role}] {m.content[:120]}" for m in history if m.role != "system"][-10:]
            return CommandResult(output="\n".join(lines) if lines else "No history.")
        return CommandResult(output="Sub: show, load, unload, send, broadcast, coordinate, crossref, clear, history")


class ScrapeCommand(Command):
    name = "scrape"
    description = "Scrape web for training data"
    async def run(self, inp: str, ctx: CommandContext) -> CommandResult:
        args = inp.strip().split()
        sub = args[0] if args else "topics"
        sc = ctx.scraper
        dm = ctx.dataset_manager
        if sub == "topics":
            return CommandResult(output=f"Topics: {', '.join(sc.get_topics())}\nUsage: /scrape topic <dataset> <topic>")
        elif sub == "topic":
            ds = args[1] if len(args) > 1 else None
            topic = args[2] if len(args) > 2 else None
            if not ds or not topic:
                return CommandResult(output="Usage: /scrape topic <dataset> <topic>")
            try: dm.create_dataset(ds, f"Scraped: {topic}")
            except: pass
            results = await sc.scrape_topic(dm, ds, topic)
            total = sum(r.get("examples", 0) for r in results)
            return CommandResult(output=f"Scraped {total} examples from {len(results)} sources into [cyan]{ds}[/].")
        elif sub == "url":
            ds = args[1] if len(args) > 1 else None
            url = args[2] if len(args) > 2 else None
            if not ds or not url:
                return CommandResult(output="Usage: /scrape url <dataset> <url>")
            try: dm.create_dataset(ds)
            except: pass
            r = await sc.scrape_to_dataset(dm, ds, {"url": url, "type": "docs", "label": url})
            msg = f"Scraped {r.get('examples', 0)} examples."
            if r.get("error"): msg += f" Error: {r['error']}"
            return CommandResult(output=msg)
        elif sub == "github":
            ds = args[1] if len(args) > 1 else None
            url = args[2] if len(args) > 2 else None
            if not ds or not url:
                return CommandResult(output="Usage: /scrape github <dataset> <github_url>")
            try: dm.create_dataset(ds)
            except: pass
            results = await sc.scrape_github_repo(dm, ds, url)
            total = sum(r.get("examples", 0) for r in results)
            return CommandResult(output=f"Scraped {total} examples from GitHub into [cyan]{ds}[/].")
        return CommandResult(output="Sub: topics, topic <ds> <topic>, url <ds> <url>, github <ds> <url>")


# ── Command list for /help ────────────────────────────────────
COMMAND_LIST = [
    ("help", "Show commands"), ("hub", "Dashboard"), ("model <n>", "Switch model"),
    ("dataset <sub>", "Manage datasets"), ("scrape <sub>", "Scrape web"),
    ("train <sub>", "Build models"), ("eval <sub>", "Evaluate"),
    ("deploy <n> <path>", "Deploy agent"), ("agents", "List agents"),
    ("launch <n>", "Launch agent"), ("undeploy <n>", "Remove agent"),
    ("templates", "Presets"), ("slots <sub>", "Model slots"),
    ("tasks", "Tasks"), ("buddy", "Companion"), ("memory", "Memory"),
    ("dream", "Consolidate"), ("compact", "Compact"), ("status", "Status"),
    ("save", "Save"), ("clear", "Clear"), ("exit", "Quit"),
]


def create_commands() -> dict[str, Command]:
    cmds = [HelpCommand(), ModelCommand(), ClearCommand(), SaveCommand(), CompactCommand(),
            StatusCommand(), ExitCommand(), TasksCommand(), BuddyCommand(), MemoryCommand(),
            DreamCommand(), HubCommand(), DatasetCommand(), TrainCommand(), EvalCommand(),
            DeployCommand(), AgentsCommand(), LaunchCommand(), UndeployCommand(),
            TemplatesCommand(), SlotsCommand(), ScrapeCommand()]
    registry: dict[str, Command] = {}
    for cmd in cmds:
        registry[cmd.name] = cmd
        for alias in getattr(cmd, "aliases", []):
            registry[alias] = cmd
    return registry
