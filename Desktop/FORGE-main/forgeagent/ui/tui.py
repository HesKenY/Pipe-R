"""ForgeAgent TUI — Button-driven terminal interface with Textual."""
from __future__ import annotations
import asyncio, logging, os, re as _re
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, RichLog, Rule, ProgressBar
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual import work

from .wizards import AutoTrainWizard, ImproveWizard, DeployWizard, RetrainWizard, ContinueTrainWizard, ToolInputModal, InfoModal, ModelSelectWizard
from .automation import run_auto_train, run_improve, run_retrain, run_continue_train, run_benchmark, run_coding_test

# ── Logging ───────────────────────────────────────────────────
_LD = Path(os.environ.get("FORGEAGENT_HOME", ".")) / ".memory"
_LD.mkdir(parents=True, exist_ok=True)
LOG_FILE = _LD / "forgeagent.log"
log = logging.getLogger("forgeagent.tui")
if not log.handlers:
    log.addHandler(logging.FileHandler(LOG_FILE, encoding="utf-8"))
    log.setLevel(logging.DEBUG)
log.info("=== TUI module loaded ===")


# ── Tool button definitions ──────────────────────────────────
# (button_label, modal_title, field_label, placeholder, message_template)
TOOL_BUTTONS = [
    ("Read File",   "Read File",   "File path",    "package.json",         "Read the file {value}"),
    ("Write File",  "Write File",  "File path",    "hello.py",             "Create a file called {value}"),
    ("Run Command", "Run Command", "Command",      "npm test",             "Run this command: {value}"),
    ("Search",      "Search Code", "Search for",   "TODO",                 "Search the codebase for {value}"),
    ("List Files",  "List Files",  "Directory",    ". (current directory)", "List the files in {value}"),
    ("Fetch URL",   "Fetch URL",   "URL",          "https://example.com",  "Fetch the URL {value}"),
]


# ══════════════════════════════════════════════════════════════
#  STATUS BAR
# ══════════════════════════════════════════════════════════════
class StatusBar(Static):
    """Thin bar showing system state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: top;
        background: $primary-background;
        color: $text-muted;
        padding: 0 2;
    }
    """

    def __init__(self):
        super().__init__("")
        self._ollama = False
        self._model = "forgeagent"
        self._datasets = 0
        self._training = "idle"

    def set_ollama(self, connected: bool):
        self._ollama = connected
        self._refresh()

    def set_model(self, name: str):
        self._model = name
        self._refresh()

    def set_datasets(self, count: int):
        self._datasets = count
        self._refresh()

    def set_training(self, status: str):
        self._training = status
        self._refresh()

    def _refresh(self):
        oc = "[green]Connected[/]" if self._ollama else "[red]Disconnected[/]"
        tc = "[yellow]" + self._training + "[/]" if self._training != "idle" else "[dim]idle[/]"
        self.update(
            f"  Ollama: {oc}  |  Model: [cyan]{self._model}[/]  |"
            f"  Datasets: {self._datasets}  |  Training: {tc}"
        )


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════
class ForgeAgentApp(App):
    TITLE = "ForgeAgent"
    SUB_TITLE = "Local AI Coding Agent"

    CSS = """
    /* ── Layout ─────────────────────────────────── */
    Screen { background: $surface; }
    #shell { height: 100%; }

    /* ── Sidebar ────────────────────────────────── */
    #sidebar {
        width: 26; height: 100%;
        background: $panel;
        border-right: tall $primary-background-lighten-1;
        padding: 0;
    }
    #sidebar-scroll { height: 1fr; padding: 0; }

    /* Section headers */
    .section-header {
        color: $text-muted; text-style: bold;
        padding: 1 1 0 1; height: 2;
    }

    /* Regular buttons */
    #sidebar Button {
        width: 100%; height: 1;
        background: transparent; color: $text-muted;
        border: none; padding: 0 1; margin: 0;
    }
    #sidebar Button:hover {
        background: $primary-background-lighten-1;
        color: $text;
    }
    #sidebar Button:focus {
        background: $accent;
        color: $text; text-style: bold;
    }

    /* Hero buttons */
    #sidebar Button.hero-green {
        background: $success-darken-2; color: white;
        text-style: bold; height: 3; margin: 0 0 0 0;
    }
    #sidebar Button.hero-green:hover { background: $success; }
    #sidebar Button.hero-green:focus { background: $success; }
    #sidebar Button.hero-green.-disabled {
        background: $primary-background; color: $text-muted;
    }

    #sidebar Button.hero-blue {
        background: $primary-darken-2; color: white;
        text-style: bold; height: 3; margin: 0 0 0 0;
    }
    #sidebar Button.hero-blue:hover { background: $primary; }
    #sidebar Button.hero-blue:focus { background: $primary; }

    #sidebar Button.hero-cyan {
        background: $accent 30%; color: white;
        text-style: bold; height: 3; margin: 0 0 0 0;
    }
    #sidebar Button.hero-cyan:hover { background: $accent 50%; }
    #sidebar Button.hero-cyan:focus { background: $accent 50%; }

    /* ── Chat area ──────────────────────────────── */
    #main { width: 1fr; }
    #chatlog {
        height: 1fr;
        padding: 1 2;
        scrollbar-size: 1 1;
        background: $surface;
    }
    #input-row {
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    #userinput {
        width: 1fr;
        border: round $primary-background-lighten-2;
        padding: 0 1;
    }
    #userinput:focus {
        border: round $accent;
    }
    #send-btn {
        width: 8; height: 3;
        background: $accent; color: $text;
        text-style: bold; border: none;
        margin: 0 0 0 1;
    }
    #send-btn:hover { background: $accent 80%; }

    /* ���─ Progress panel ─────────────────────────── */
    #progress-panel {
        height: auto; padding: 0 1; margin: 0;
        display: none;
    }
    #progress-panel.visible { display: block; }
    #progress-label {
        color: $text-muted; height: 1; padding: 0;
    }
    #progress-bar {
        margin: 0; padding: 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+s", "do_save", "Save"),
        Binding("ctrl+l", "do_clear", "Clear log"),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    def __init__(self, ctx: dict):
        super().__init__()
        self.ctx = ctx
        self.engine = ctx["engine"]
        self.commands = ctx["commands"]
        self.config = ctx["config"]
        self.buddy = ctx["buddy"]
        self.memory = ctx["memory"]
        self.setup_status = ctx.get("setup_status", {})
        self.turn = 0
        self._training_active = False
        log.info(f"init model={self.config.model}")

    # ── Layout ────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar()
        with Horizontal(id="shell"):
            with Vertical(id="sidebar"):
                with VerticalScroll(id="sidebar-scroll"):
                    # Hero buttons
                    yield Static("Get Started", classes="section-header")
                    yield Button("AUTO TRAIN", id="btn-auto-train", classes="hero-green")
                    yield Button("IMPROVE MODEL", id="btn-improve", classes="hero-blue")
                    yield Button("DEPLOY AGENT", id="btn-deploy", classes="hero-cyan")

                    # Training buttons
                    yield Static("Training", classes="section-header")
                    yield Button("Continue Training", id="btn-continue-train")
                    yield Button("Retrain from Scratch", id="btn-retrain")

                    # Progress panel (hidden by default)
                    with Vertical(id="progress-panel"):
                        yield Static("", id="progress-label")
                        yield ProgressBar(id="progress-bar", total=100, show_eta=False, show_percentage=True)

                    # Chat tools
                    yield Static("Chat Tools", classes="section-header")
                    for i, (label, *_rest) in enumerate(TOOL_BUTTONS):
                        yield Button(label, id=f"btn-tool-{i}")

                    # Management
                    yield Static("Manage", classes="section-header")
                    yield Button("Models", id="btn-models")
                    yield Button("Datasets", id="btn-datasets")
                    yield Button("Agents", id="btn-agents")
                    yield Button("Evaluate", id="btn-evaluate")
                    yield Button("Code Test", id="btn-codetest")
                    yield Button("Benchmark vs Claude", id="btn-benchmark")

                    # Session
                    yield Static("Session", classes="section-header")
                    yield Button("Save", id="btn-save")
                    yield Button("Clear", id="btn-clear")
                    yield Button("Compact", id="btn-compact")
                    yield Button("Buddy", id="btn-buddy")

            with Vertical(id="main"):
                yield RichLog(id="chatlog", wrap=True, highlight=True, markup=True)
                with Horizontal(id="input-row"):
                    yield Input(placeholder="Message ForgeAgent...  (or just click a button)", id="userinput")
                    yield Button("Send", id="send-btn")
        yield Footer()

    # ── Startup ───────────────────────────────────
    async def on_mount(self):
        log.info("on_mount")
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)

        # Ollama check
        try:
            alive = await self.engine.client.ping()
            status_bar.set_ollama(alive)
            if alive:
                self.notify("Connected to Ollama", timeout=3)
            else:
                self.notify("Ollama not reachable — start it with: ollama serve", severity="warning", timeout=8)
                log.warning("ollama unreachable")
        except Exception as e:
            status_bar.set_ollama(False)
            self.notify(f"Ollama error: {e}", severity="error", timeout=8)
            log.error(f"ping: {e}")

        # Status bar — model and datasets
        status_bar.set_model(self.config.model)
        try:
            nd = len(self.ctx["dataset_manager"].list_datasets())
            status_bar.set_datasets(nd)
        except Exception:
            pass

        # Auto-restore session
        try:
            last = await self.ctx["session_store"].load_latest()
            if last and len(last) > 2:
                self.engine.restore_messages(last)
                self.notify(f"Session restored ({len(last)} messages)", timeout=3)
        except Exception as e:
            log.error(f"restore: {e}")

        # Setup status messages
        if self.setup_status.get("env_created"):
            chat.write("  [yellow]First run detected — .env created from defaults.[/]")
        if self.setup_status.get("ollama_auto_started"):
            chat.write("  [green]Ollama started automatically.[/]")
        if not self.setup_status.get("ollama_running"):
            import shutil
            has_ollama = shutil.which("ollama") is not None
            if has_ollama:
                chat.write("  [yellow]Ollama is installed but not running.[/]")
                chat.write("  [dim]Start it by running:[/]  [bold]ollama serve[/]")
            else:
                chat.write("  [red]Ollama is not installed.[/]")
                chat.write("")
                chat.write("  [bold]How to install Ollama:[/]")
                chat.write("  [dim]1. Go to[/]  [bold cyan]https://ollama.com/download[/]")
                chat.write("  [dim]2. Download and run the Windows installer[/]")
                chat.write("  [dim]3. Restart ForgeAgent — it will auto-start Ollama[/]")
            chat.write("")

        # Welcome
        b = self.buddy.summary
        try:
            na = len(self.ctx["deployer"].list_agents())
        except Exception:
            na = 0

        chat.write("")
        chat.write(f"  [bold cyan]ForgeAgent[/]")
        chat.write(f"  [dim]Local AI Coding Agent — 100% Offline[/]")
        chat.write("")
        chat.write(f"  [dim]Buddy:[/]  [yellow]{b.name} Lv.{b.level}[/]    "
                    f"[dim]Agents:[/]  {na}    "
                    f"[dim]Model:[/]  [cyan]{self.config.model}[/]")
        chat.write(f"  [dim italic]{self.buddy.get_quip()}[/]")
        chat.write("")
        chat.write(f"  [bold]Click a button to get started:[/]")
        chat.write(f"  [green]AUTO TRAIN[/]  — Build your own AI model in one click")
        chat.write(f"  [blue]IMPROVE[/]     — Make your model smarter with more data")
        chat.write(f"  [cyan]DEPLOY[/]      — Set up an agent in your project folder")
        chat.write("")
        chat.write(f"  [dim]Or just type a message to start chatting.[/]")
        chat.write("")

        self.query_one("#userinput", Input).focus()
        log.info("mount complete")

    # ── Keybindings ───────────────────────────────
    async def action_do_save(self):
        await self.engine.save_session()
        self.notify("Session saved", timeout=2)

    def action_do_clear(self):
        self.query_one("#chatlog", RichLog).clear()

    def action_focus_input(self):
        self.query_one("#userinput", Input).focus()

    # ── Progress panel helpers ────────────────────
    def _show_progress(self, label: str, step: int, total: int):
        panel = self.query_one("#progress-panel")
        panel.add_class("visible")
        self.query_one("#progress-label", Static).update(f"[bold]{label}[/]")
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(total=total, progress=step)

    def _hide_progress(self):
        panel = self.query_one("#progress-panel")
        panel.remove_class("visible")
        self.query_one("#progress-label", Static).update("")

    # ── Button clicks ─────────────────────────────
    async def on_button_pressed(self, e: Button.Pressed):
        bid = e.button.id or ""
        log.info(f"button: {bid}")

        # ── Hero buttons ──────────────────────────
        if bid == "btn-auto-train":
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            models = self.ctx["model_builder"].list_local_models()
            self.push_screen(AutoTrainWizard(installed_models=models), callback=self._on_auto_train)
        elif bid == "btn-improve":
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            models = self.ctx["model_builder"].list_local_models()
            self.push_screen(ImproveWizard(self.config.model, installed_models=models), callback=self._on_improve)
        elif bid == "btn-deploy":
            self.push_screen(DeployWizard(self.config.model), callback=self._on_deploy)

        # ── Training buttons ──────────────────────
        elif bid == "btn-continue-train":
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            self.push_screen(ContinueTrainWizard(self.config.model), callback=self._on_continue_train)
        elif bid == "btn-retrain":
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            self.push_screen(RetrainWizard(self.config.model), callback=self._on_retrain)

        # ── Chat tool buttons ─────────────────────
        elif bid.startswith("btn-tool-"):
            idx = int(bid.split("-")[-1])
            if idx < len(TOOL_BUTTONS):
                _, title, field_label, placeholder, template = TOOL_BUTTONS[idx]
                self.push_screen(
                    ToolInputModal(title, field_label, placeholder, template),
                    callback=self._on_tool_input,
                )

        # ── Management buttons ────────────────────
        elif bid == "btn-models":
            await self._show_models()
        elif bid == "btn-datasets":
            await self._show_datasets()
        elif bid == "btn-agents":
            await self._show_agents()
        elif bid == "btn-evaluate":
            if self._training_active:
                self.notify("Training in progress — please wait", severity="warning", timeout=3)
                return
            self._do_evaluate()
        elif bid == "btn-codetest":
            if self._training_active:
                self.notify("Training in progress — please wait", severity="warning", timeout=3)
                return
            self._do_code_test(self.config.model)
        elif bid == "btn-benchmark":
            if self._training_active:
                self.notify("Training in progress — please wait", severity="warning", timeout=3)
                return
            self._do_benchmark(self.config.model)

        # ── Session buttons ───────────────────────
        elif bid == "btn-save":
            await self.engine.save_session()
            self.notify("Session saved", timeout=2)
        elif bid == "btn-clear":
            self.query_one("#chatlog", RichLog).clear()
        elif bid == "btn-compact":
            chat = self.query_one("#chatlog", RichLog)
            chat.write("  [dim]Compacting conversation...[/]")
            await self.engine.compact()
            chat.write("  [green]Conversation compacted.[/]")
        elif bid == "btn-buddy":
            b = self.buddy.summary
            self.push_screen(InfoModal("Buddy", (
                f"[yellow]{b.name}[/]  Level {b.level}\n"
                f"XP: {b.xp}  Mood: {b.mood}\n\n"
                f"[dim italic]{self.buddy.get_quip()}[/]"
            )))

        # ── Send button ──────────────────────────
        elif bid == "send-btn":
            inp = self.query_one("#userinput", Input)
            if inp.value.strip():
                # Trigger the same flow as Enter
                await self._handle_input(inp.value.strip())
                inp.value = ""

    # ── Text input (Enter key) ────────────────────
    async def on_input_submitted(self, e: Input.Submitted):
        text = e.value.strip()
        if not text:
            return
        e.input.value = ""
        await self._handle_input(text)

    async def _handle_input(self, text: str):
        chat = self.query_one("#chatlog", RichLog)
        log.info(f"input: {text[:80]!r}")

        # ── Slash commands (power users) ──────────
        if text.startswith("/"):
            parts = text[1:].split(" ", 1)
            name, arg = parts[0], parts[1] if len(parts) > 1 else ""
            cmd = self.commands.get(name)
            if not cmd:
                self.notify(f"Unknown command: /{name}", severity="warning", timeout=3)
                return
            chat.write(f"  [dim]> /{name} {arg}[/]")
            try:
                from ..core.interfaces import CommandContext
                ctx = CommandContext(
                    config=self.config, engine=self.engine, buddy=self.buddy,
                    memory=self.memory, session_store=self.ctx["session_store"],
                    deployer=self.ctx["deployer"], dataset_manager=self.ctx["dataset_manager"],
                    model_builder=self.ctx["model_builder"], evaluator=self.ctx["evaluator"],
                    scraper=self.ctx["scraper"], instance_manager=self.ctx["instance_manager"],
                )
                r = await cmd.run(arg, ctx)
                if r.output:
                    for line in r.output.split("\n"):
                        chat.write(f"  {line}")
                if r.should_exit:
                    await self.engine.save_session()
                    self.exit()
            except Exception as ex:
                chat.write(f"  [red]Error: {ex}[/]")
                log.error(f"cmd /{name}: {ex}", exc_info=True)
            return

        # ── @N slot shorthand ─────────────────────
        m = _re.match(r"^@(\d)\s+(.+)", text)
        if m:
            slot, msg = int(m.group(1)), m.group(2)
            chat.write(f"  [cyan]@{slot}[/] {msg}")
            try:
                resp = await self.ctx["instance_manager"].send_to_slot(slot, msg)
                chat.write(f"  [green]Slot {slot}:[/] {resp[:2000]}")
            except Exception as ex:
                chat.write(f"  [red]Slot {slot}: {ex}[/]")
            return

        # ── Normal chat ───────────────────────────
        chat.write(f"\n  [bold cyan]You[/]")
        chat.write(f"  {text}")
        self.turn += 1
        self.buddy.on_interaction()

        try:
            result = await self.engine.submit_user_message(text)

            if result.tool_calls:
                names = ", ".join(tc.tool_name for tc in result.tool_calls)
                chat.write(f"  [dim]tools: {names}[/]")
                for _ in result.tool_calls:
                    self.buddy.on_tool_use()

            chat.write(f"\n  [bold green]ForgeAgent[/]")
            chat.write(f"  {result.assistant_message.content}")
            chat.write("")

            # Auto-dream
            if self.turn > 0 and self.turn % self.config.dream_interval == 0:
                self.notify("Dreaming...", timeout=2)
                await self.memory.dream(self.engine.summarize, self.engine.get_messages())
                self.buddy.on_dream()
                log.info("auto-dream done")
        except Exception as ex:
            chat.write(f"  [red]Error: {ex}[/]")
            log.error(f"chat: {ex}", exc_info=True)

    # ── Tool input callback ───────────────────────
    async def _on_tool_input(self, message: str | None):
        if message:
            await self._handle_input(message)

    # ── Auto Train callback ───────────────────────
    async def _on_auto_train(self, r: dict | None):
        if not r:
            return
        # If user selected an existing model, run it through refined training
        if r.get("existing_model"):
            self._do_refine_existing(r)
        else:
            self._do_auto_train(r)

    @work(thread=False, exclusive=True, group="training")
    async def _do_refine_existing(self, config: dict) -> None:
        """Refine an existing model — create/update profile, add data, rebuild."""
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("refining...")

        existing = config["existing_model"]
        focus = config.get("focus", "general")
        name = config.get("name") or existing

        chat.write(f"\n  [bold green]Refining existing model: {existing}[/]")
        chat.write(f"  [dim]Focus: {focus} | Output model: {name}[/]")
        chat.write("")

        from .automation import FOCUS_MAP, run_auto_train

        # If name differs from existing, we're creating a variant
        # Set the config to use the existing model's base
        mb = self.ctx["model_builder"]
        profile = mb.get_profile(existing)

        if profile:
            # Use existing profile's base model
            base = profile["baseModel"]
            size_key = "balanced"
            for sk, bk in [("fast", "base_7b"), ("balanced", "base_14b"), ("powerful", "base_32b")]:
                focus_info = FOCUS_MAP.get(focus, FOCUS_MAP["general"])
                if focus_info[bk] == base:
                    size_key = sk
                    break
            config["size"] = size_key
            if name != existing:
                config["name"] = name
        else:
            # No profile — treat as continue training with full data collection
            pass

        config["name"] = name

        def on_step(step, total, message):
            try:
                chat.write(f"  [dim][{step}/{total}][/] {message}")
                status_bar.set_training(f"step {step}/{total}")
                self._show_progress(message[:30], step, total)
            except Exception:
                pass

        try:
            result = await run_auto_train(self.ctx, config, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold green]Model '{result['model_name']}' refined![/]")
                ex = result["examples"]
                chat.write(f"  [dim]Training data: {ex['synthetic']} synthetic + {ex['scraped']} scraped + {ex['codebase']} codebase[/]")
                smoke = result["smoke"]
                if smoke.get("alive"):
                    chat.write(f"  [green]Smoke test: PASSED[/]")
                chat.write(f"  [dim]Build time: {result['duration']:.1f}s[/]")
                chat.write("")

                self.engine.set_model(result["model_name"])
                self.config.model = result["model_name"]
                status_bar.set_model(result["model_name"])
                chat.write(f"  [bold green]Switched to model: {result['model_name']}[/]")
                chat.write("")
                self.notify(f"Model refined!", severity="information", timeout=8)
            else:
                chat.write(f"\n  [red]Refinement failed: {result.get('error', 'unknown')}[/]")
        except Exception as ex:
            chat.write(f"\n  [red]Refinement error: {ex}[/]")
            log.error(f"refine: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    @work(thread=False, exclusive=True, group="training")
    async def _do_auto_train(self, config: dict) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("training...")

        chat.write(f"\n  [bold green]Starting Auto Train[/]")
        chat.write(f"  [dim]Focus: {config['focus']} | Size: {config['size']}[/]")
        chat.write("")

        def on_step(step, total, message):
            # May be called from a background thread (e.g. during model pull)
            try:
                chat.write(f"  [dim][{step}/{total}][/] {message}")
                status_bar.set_training(f"step {step}/{total}")
                self._show_progress(message[:30], step, total)
            except Exception:
                pass  # Swallow thread-safety errors during rapid progress updates

        try:
            result = await run_auto_train(self.ctx, config, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold green]Model '{result['model_name']}' is ready![/]")
                chat.write(f"  [dim]Base: {result['base_model']}[/]")
                ex = result["examples"]
                chat.write(f"  [dim]Training data: {ex['synthetic']} synthetic + {ex['scraped']} scraped + {ex['codebase']} codebase[/]")
                smoke = result["smoke"]
                if smoke.get("alive"):
                    chat.write(f"  [green]Smoke test: PASSED[/]  (chat: {'yes' if smoke.get('canChat') else 'no'}, tools: {'yes' if smoke.get('canTool') else 'no'})")
                else:
                    chat.write(f"  [yellow]Smoke test: model not responding yet (may need a moment to load)[/]")
                chat.write(f"  [dim]Build time: {result['duration']:.1f}s[/]")
                chat.write("")
                chat.write(f"  [bold green]Switched to model: {result['model_name']}[/]")
                chat.write(f"  [dim]Click DEPLOY to set up an agent in a project folder.[/]")
                self.notify(f"Model '{result['model_name']}' trained!", severity="information", timeout=8)

                # Auto-switch to the new model
                self.engine.set_model(result["model_name"])
                self.config.model = result["model_name"]

                # Update status bar
                status_bar.set_model(result["model_name"])
                try:
                    nd = len(self.ctx["dataset_manager"].list_datasets())
                    status_bar.set_datasets(nd)
                except Exception:
                    pass
            else:
                chat.write(f"\n  [red]Training failed at step '{result.get('step', '?')}': {result.get('error', 'unknown')}[/]")
                self.notify("Training failed", severity="error", timeout=8)
        except Exception as ex:
            chat.write(f"\n  [red]Training error: {ex}[/]")
            log.error(f"auto_train: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Improve callback ──────────────────────────
    async def _on_improve(self, r: dict | None):
        if not r:
            return
        self._do_improve(r)

    @work(thread=False, exclusive=True, group="training")
    async def _do_improve(self, config: dict) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("improving...")

        chat.write(f"\n  [bold blue]Improving model: {config['model_name']}[/]")

        def on_step(step, total, message):
            chat.write(f"  [dim][{step}/{total}][/] {message}")
            status_bar.set_training(f"step {step}/{total}")
            self._show_progress(message[:30], step, total)

        try:
            result = await run_improve(self.ctx, config, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold green]Model improved![/]")
                added = result.get("added", {})
                chat.write(f"  [dim]Data added: {added.get('synthetic', 0)} synthetic, "
                           f"{added.get('conversations', 0)} conversation, "
                           f"{added.get('codebase', 0)} codebase, "
                           f"{added.get('scraped', 0)} scraped[/]")
                chat.write(f"  [dim]Total training examples: {result.get('total_examples', '?')}[/]")
                if result["before_score"] or result["after_score"]:
                    before = result["before_score"]
                    after = result["after_score"]
                    diff = result["improvement"]
                    color = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
                    chat.write(f"  Score: {before}% -> [{color}]{after}%[/]  ({'+' if diff >= 0 else ''}{diff}%)")
                chat.write("")
                self.notify("Model improved!", severity="information", timeout=5)
            else:
                chat.write(f"\n  [red]Improvement failed: {result.get('error', 'unknown')}[/]")
        except Exception as ex:
            chat.write(f"\n  [red]Improvement error: {ex}[/]")
            log.error(f"improve: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Retrain callback ─────────────────────────
    async def _on_retrain(self, r: dict | None):
        if not r:
            return
        self._do_retrain(r)

    @work(thread=False, exclusive=True, group="training")
    async def _do_retrain(self, config: dict) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("retraining...")

        chat.write(f"\n  [bold yellow]Retraining model: {config['model_name']}[/]")
        chat.write(f"  [dim]Focus: {config.get('focus', 'general')} | Fresh data from scratch[/]")
        chat.write("")

        def on_step(step, total, message):
            chat.write(f"  [dim][{step}/{total}][/] {message}")
            status_bar.set_training(f"step {step}/{total}")
            self._show_progress(message[:30], step, total)

        try:
            result = await run_retrain(self.ctx, config, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold green]Model '{result['model_name']}' retrained![/]")
                ex = result["examples"]
                chat.write(f"  [dim]Fresh data: {ex['synthetic']} synthetic + {ex['scraped']} scraped + {ex['codebase']} codebase + {ex['conversations']} conversation[/]")
                smoke = result["smoke"]
                if smoke.get("alive"):
                    chat.write(f"  [green]Smoke test: PASSED[/]")
                chat.write(f"  [dim]Build time: {result['duration']:.1f}s[/]")
                chat.write("")
                self.notify(f"Model retrained!", severity="information", timeout=8)
            else:
                chat.write(f"\n  [red]Retrain failed: {result.get('error', 'unknown')}[/]")
                self.notify("Retrain failed", severity="error", timeout=8)
        except Exception as ex:
            chat.write(f"\n  [red]Retrain error: {ex}[/]")
            log.error(f"retrain: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Continue Training callback ────────────────
    async def _on_continue_train(self, r: dict | None):
        if not r:
            return
        self._do_continue_train(r)

    @work(thread=False, exclusive=True, group="training")
    async def _do_continue_train(self, config: dict) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("continuing...")

        chat.write(f"\n  [bold blue]Continue training: {config['model_name']}[/]")
        chat.write("")

        def on_step(step, total, message):
            chat.write(f"  [dim][{step}/{total}][/] {message}")
            status_bar.set_training(f"step {step}/{total}")
            self._show_progress(message[:30], step, total)

        try:
            result = await run_continue_train(self.ctx, config, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold green]Training continued![/]")
                added = result["added"]
                chat.write(f"  [dim]Added: {added['synthetic']} synthetic + {added['scraped']} scraped + {added['codebase']} codebase + {added['conversations']} conversation[/]")
                if result["before_score"] or result["after_score"]:
                    before = result["before_score"]
                    after = result["after_score"]
                    diff = result["improvement"]
                    color = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
                    chat.write(f"  Score: {before}% -> [{color}]{after}%[/]  ({'+' if diff >= 0 else ''}{diff}%)")
                chat.write(f"  [dim]Build time: {result['duration']:.1f}s[/]")
                chat.write("")
                self.notify("Training continued!", severity="information", timeout=5)
            else:
                chat.write(f"\n  [red]Continue training failed: {result.get('error', 'unknown')}[/]")
        except Exception as ex:
            chat.write(f"\n  [red]Continue training error: {ex}[/]")
            log.error(f"continue_train: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Deploy callback ───────────────────────────
    async def _on_deploy(self, r: dict | None):
        if not r:
            return
        chat = self.query_one("#chatlog", RichLog)
        if not r.get("path"):
            self.notify("No path provided", severity="warning", timeout=3)
            return
        log.info(f"deploy: {r}")
        try:
            agent = self.ctx["deployer"].deploy(r["name"], r["path"], r["model"], r["template"])
            chat.write(f"\n  [bold green]Deployed: {agent['name']}[/]")
            chat.write(f"  [dim]Path: {agent['projectPath']}[/]")
            chat.write(f"  [dim]Template: {r['template']} | Model: {r['model']}[/]")
            chat.write(f"  [dim]To launch: /launch {agent['name']}[/]")
            chat.write("")
            self.notify(f"Agent '{agent['name']}' deployed!", timeout=5)
        except Exception as ex:
            chat.write(f"  [red]Deploy failed: {ex}[/]")
            log.error(f"deploy: {ex}", exc_info=True)

    # ── Management info modals ────────────────────
    async def _show_models(self):
        mb = self.ctx["model_builder"]
        models = mb.list_local_models()
        profiles = mb.list_profiles()
        self.push_screen(
            ModelSelectWizard(models, self.config.model, profiles),
            callback=self._on_model_select,
        )

    async def _on_model_select(self, r: dict | None):
        if not r:
            return
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)

        if r["action"] == "use":
            model_name = r["model"]
            self.engine.set_model(model_name)
            self.config.model = model_name
            status_bar.set_model(model_name)
            chat.write(f"\n  [bold green]Switched to model: {model_name}[/]")
            chat.write("")
            self.notify(f"Now using: {model_name}", timeout=3)

        elif r["action"] == "train":
            model_name = r["model"]
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            self.push_screen(
                ContinueTrainWizard(model_name),
                callback=self._on_continue_train,
            )

        elif r["action"] == "retrain":
            model_name = r["model"]
            if self._training_active:
                self.notify("Training already in progress", severity="warning", timeout=3)
                return
            self.push_screen(
                RetrainWizard(model_name),
                callback=self._on_retrain,
            )

        elif r["action"] == "benchmark":
            model_name = r["model"]
            if self._training_active:
                self.notify("Training in progress — please wait", severity="warning", timeout=3)
                return
            self._do_benchmark(model_name)

    async def _show_datasets(self):
        dm = self.ctx["dataset_manager"]
        datasets = dm.list_datasets()
        if not datasets:
            content = "[dim]No datasets yet. AUTO TRAIN will create one automatically.[/]"
        else:
            lines = [f"[bold]{'Name':<25} {'Examples':<10} Updated[/]", ""]
            for d in datasets:
                lines.append(f"{d['name']:<25} {d.get('exampleCount', 0):<10} {d.get('updated', '')[:10]}")
            content = "\n".join(lines)
        self.push_screen(InfoModal("Datasets", content))

    async def _show_agents(self):
        deployer = self.ctx["deployer"]
        agents = deployer.list_agents()
        if not agents:
            content = "[dim]No agents deployed. Click DEPLOY AGENT to set one up.[/]"
        else:
            lines = [f"[bold]{'Name':<20} {'Model':<25} {'Template':<12} Status[/]", ""]
            for a in agents:
                lines.append(f"{a['name']:<20} {a.get('modelName', '?'):<25} {a.get('template', '?'):<12} {a.get('status', '?')}")
            content = "\n".join(lines)
        self.push_screen(InfoModal("Deployed Agents", content))

    @work(thread=False, exclusive=True, group="training")
    async def _do_evaluate(self) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("evaluating...")

        chat.write(f"\n  [bold]Evaluating model: {self.config.model}[/]")

        def on_progress(i, total, result):
            status = "[green]PASS[/]" if result["passed"] else "[red]FAIL[/]"
            chat.write(f"  [{i}/{total}] {result['prompt'][:50]}... {status}")
            self._show_progress("Evaluating...", i, total)

        try:
            ev = self.ctx["evaluator"]
            report = await ev.evaluate(self.config.model, on_progress=on_progress)
            chat.write("")
            chat.write(f"  [bold]Results: {report['passed']}/{report['totalCases']} passed  |  Score: {report['avgScore']}%  |  Avg latency: {report['avgLatencyMs']}ms[/]")
            for cat, data in report.get("byCategory", {}).items():
                chat.write(f"  [dim]{cat}: {data['passed']}/{data['total']} passed[/]")
            chat.write("")
        except Exception as ex:
            chat.write(f"  [red]Evaluation error: {ex}[/]")
            log.error(f"evaluate: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Code Test: auto-graded coding challenges ──
    @work(thread=False, exclusive=True, group="training")
    async def _do_code_test(self, model_name: str) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("code testing...")

        chat.write(f"\n  [bold cyan]Coding Test: {model_name}[/]")
        chat.write(f"  [dim]8 challenges (easy/medium/hard) — auto-graded by running the code[/]")
        chat.write("")

        def on_step(step, total, message):
            try:
                chat.write(f"  [dim][{step}/{total}][/] {message}")
                status_bar.set_training(f"test {step}/{total}")
                self._show_progress(message[:30], step, total)
            except Exception:
                pass

        try:
            result = await run_coding_test(self.ctx, model_name, on_step)

            if result["success"]:
                chat.write("")
                chat.write(f"  [bold]{'='*50}[/]")
                chat.write(f"  [bold]  CODING TEST RESULTS[/]")
                chat.write(f"  [bold]{'='*50}[/]")
                chat.write("")
                chat.write(f"  [bold]Score: {result['pct']}%  ({result['passed']}/{result['total']} passed)[/]")
                chat.write(f"  [dim]Avg latency: {result['avg_latency']}ms[/]")
                chat.write("")

                # By difficulty
                chat.write(f"  [bold]By Difficulty:[/]")
                for diff in ["easy", "medium", "hard"]:
                    data = result["by_difficulty"].get(diff, {"passed": 0, "total": 0})
                    pct = round(data["passed"] / data["total"] * 100) if data["total"] else 0
                    bar = "[green]" + "#" * data["passed"] + "[/][red]" + "#" * (data["total"] - data["passed"]) + "[/]"
                    chat.write(f"  {diff:<10} {data['passed']}/{data['total']}  {bar}  {pct}%")
                chat.write("")

                # Per-case results
                chat.write(f"  [bold]Per-Challenge:[/]")
                for r in result["results"]:
                    icon = "[green]PASS[/]" if r["passed"] else "[red]FAIL[/]"
                    diff_color = {"easy": "green", "medium": "yellow", "hard": "red"}.get(r["difficulty"], "white")
                    chat.write(f"  {icon}  [{diff_color}]{r['difficulty']:<8}[/]  {r['prompt'][:50]}")
                    if not r["passed"]:
                        chat.write(f"         [dim red]{r['output'][:80]}[/]")
                chat.write("")

                self.notify(f"Code test: {result['pct']}% ({result['passed']}/{result['total']})", timeout=5)
        except Exception as ex:
            chat.write(f"\n  [red]Code test error: {ex}[/]")
            log.error(f"code_test: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()

    # ── Benchmark: local model vs Claude API ──────
    @work(thread=False, exclusive=True, group="training")
    async def _do_benchmark(self, model_name: str) -> None:
        chat = self.query_one("#chatlog", RichLog)
        status_bar = self.query_one(StatusBar)
        self._training_active = True
        status_bar.set_training("benchmarking...")

        chat.write(f"\n  [bold cyan]Benchmark: {model_name} vs Claude API[/]")
        chat.write("")

        def on_step(step, total, message):
            try:
                chat.write(f"  [dim][{step}/{total}][/] {message}")
                status_bar.set_training(f"bench {step}/{total}")
                self._show_progress(message[:30], step, total)
            except Exception:
                pass

        try:
            result = await run_benchmark(self.ctx, model_name, on_step)

            if result["success"]:
                local = result["local"]
                chat.write("")
                chat.write(f"  [bold]{'='*58}[/]")
                chat.write(f"  [bold]  BENCHMARK RESULTS — {result['cases']} test cases[/]")
                chat.write(f"  [bold]{'='*58}[/]")
                chat.write("")

                # Header
                chat.write(f"  [bold]{'Metric':<25} {'Local':<15} {'Claude API':<15}[/]")
                chat.write(f"  {'─'*55}")

                # Overall
                local_pct = f"{local['pct']}%"
                local_lat = f"{local['avg_latency']}ms"
                local_pass = f"{local['passed']}/{local['total']}"

                if result["has_claude"]:
                    claude = result["claude"]
                    claude_pct = f"{claude['pct']}%"
                    claude_lat = f"{claude['avg_latency']}ms"
                    claude_pass = f"{claude['passed']}/{claude['total']}"
                else:
                    claude_pct = claude_lat = claude_pass = "[dim]no API key[/]"

                chat.write(f"  {'Score':<25} [bold]{local_pct:<15}[/] [bold]{claude_pct:<15}[/]")
                chat.write(f"  {'Passed':<25} {local_pass:<15} {claude_pass:<15}")
                chat.write(f"  {'Avg Latency':<25} {local_lat:<15} {claude_lat:<15}")
                chat.write("")

                # By category
                chat.write(f"  [bold]By Category:[/]")
                all_cats = set(local.get("by_category", {}).keys())
                if result["has_claude"]:
                    all_cats |= set(result["claude"].get("by_category", {}).keys())
                for cat in sorted(all_cats):
                    lc = local.get("by_category", {}).get(cat, {"passed": 0, "total": 0})
                    local_cat = f"{lc['passed']}/{lc['total']}"
                    if result["has_claude"]:
                        cc = result["claude"].get("by_category", {}).get(cat, {"passed": 0, "total": 0})
                        claude_cat = f"{cc['passed']}/{cc['total']}"
                    else:
                        claude_cat = "—"
                    chat.write(f"  {'  ' + cat:<25} {local_cat:<15} {claude_cat:<15}")

                chat.write("")

                # Per-case comparison
                chat.write(f"  [bold]Per-Case Results:[/]")
                for i, lr in enumerate(result["local_results"]):
                    l_icon = "[green]PASS[/]" if lr["passed"] else "[red]FAIL[/]"
                    if result["has_claude"] and i < len(result["claude_results"]):
                        cr = result["claude_results"][i]
                        c_icon = "[green]PASS[/]" if cr["passed"] else "[red]FAIL[/]"
                    else:
                        c_icon = "—"
                    chat.write(f"  {lr['prompt'][:40]:<42} {l_icon}  {c_icon}")

                chat.write("")

                # Summary
                if result["has_claude"]:
                    diff = local["pct"] - result["claude"]["pct"]
                    if diff >= 0:
                        chat.write(f"  [bold green]Your model scores {'+' if diff > 0 else ''}{diff}% vs Claude Haiku.[/]")
                    else:
                        chat.write(f"  [bold yellow]Your model is {abs(diff)}% behind Claude Haiku. Continue training to close the gap.[/]")
                    speed_ratio = round(result["claude"]["avg_latency"] / max(local["avg_latency"], 1), 1) if local["avg_latency"] > 0 else 0
                    if speed_ratio > 1:
                        chat.write(f"  [dim]Your local model responds {speed_ratio}x faster (no network latency).[/]")
                else:
                    chat.write(f"  [dim]Set ANTHROPIC_API_KEY in .env to compare against Claude API.[/]")

                chat.write("")
                self.notify("Benchmark complete!", timeout=5)
            else:
                chat.write(f"\n  [red]Benchmark failed: {result.get('error', 'unknown')}[/]")
        except Exception as ex:
            chat.write(f"\n  [red]Benchmark error: {ex}[/]")
            log.error(f"benchmark: {ex}", exc_info=True)
        finally:
            self._training_active = False
            status_bar.set_training("idle")
            self._hide_progress()


# ── Entry ─────────────────────────────────────────────────────
async def start_tui(ctx: dict):
    log.info("starting TUI")
    await ForgeAgentApp(ctx).run_async()
    log.info("TUI exited")
