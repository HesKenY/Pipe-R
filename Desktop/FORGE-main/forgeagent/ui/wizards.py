"""Modal wizard dialogs for ForgeAgent TUI."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Select, Rule, Label, RichLog, Switch, DirectoryTree
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.app import ComposeResult


# ══════════════════════════════════════════════════════════════
#  AUTO TRAIN WIZARD
# ══════════════════════════════════════════════════════════════
class AutoTrainWizard(ModalScreen[dict | None]):
    """One-click model training — user picks focus and size, everything else is automated."""

    CSS = """
    AutoTrainWizard { align: center middle; }
    #atw {
        width: 60; height: 32;
        border: round $success; background: $surface;
        padding: 1 2;
    }
    #atw Static.title { text-style: bold; color: $success; margin: 0 0 1 0; }
    #atw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #atw-scroll { height: 1fr; }
    #atw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #atw-scroll Input { margin: 0; }
    #atw-scroll Select { margin: 0; }
    #atw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #atw-actions Button { min-width: 20; margin: 0 1 0 0; height: 3; }
    """

    FOCUS_OPTIONS = [
        ("Python  (FastAPI, Django, ML)", "python"),
        ("Web / Fullstack  (React, Node, TS)", "web"),
        ("Rust  (Tokio, systems)", "rust"),
        ("Go  (microservices, CLIs)", "go"),
        ("DevOps  (Docker, K8s, CI/CD)", "devops"),
        ("General  (all-purpose coding)", "general"),
    ]

    SIZE_OPTIONS = [
        ("Fast  (7B — light, quick responses)", "fast"),
        ("Balanced  (14B — recommended)", "balanced"),
        ("Powerful  (32B — best quality, slower)", "powerful"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="atw"):
            yield Static("Auto Train", classes="title")
            yield Static("Pick a focus and size. Everything else is automatic.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="atw-scroll"):
                yield Static("What kind of coding?", classes="field-label")
                yield Select(self.FOCUS_OPTIONS, value="python", id="atw-focus")
                yield Static("Model size", classes="field-label")
                yield Select(self.SIZE_OPTIONS, value="balanced", id="atw-size")
                yield Static("Model name (optional)", classes="field-label")
                yield Input(placeholder="auto-generated if blank", id="atw-name")
            with Horizontal(id="atw-actions"):
                yield Button("Start Training", variant="success", id="atw-go")
                yield Button("Cancel", id="atw-no")

    def on_mount(self):
        self.query_one("#atw-focus", Select).focus()

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "atw-no":
            self.dismiss(None)
        elif e.button.id == "atw-go":
            focus_sel = self.query_one("#atw-focus", Select)
            size_sel = self.query_one("#atw-size", Select)
            self.dismiss({
                "focus": str(focus_sel.value) if focus_sel.value != Select.BLANK else "general",
                "size": str(size_sel.value) if size_sel.value != Select.BLANK else "balanced",
                "name": self.query_one("#atw-name", Input).value.strip() or "",
            })


# ══════════════════════════════════════════════════════════════
#  IMPROVE MODEL WIZARD
# ══════════════════════════════════════════════════════════════
class ImproveWizard(ModalScreen[dict | None]):
    """Improve an existing model by adding more training data."""

    CSS = """
    ImproveWizard { align: center middle; }
    #imw {
        width: 60; height: 30;
        border: round $primary; background: $surface;
        padding: 1 2;
    }
    #imw Static.title { text-style: bold; color: $primary; margin: 0 0 1 0; }
    #imw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #imw-scroll { height: 1fr; }
    #imw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #imw-scroll Select { margin: 0; }
    #imw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #imw-actions Button { min-width: 20; margin: 0 1 0 0; height: 3; }
    .toggle-row { height: 3; padding: 0 0; }
    .toggle-row Static { padding: 1 1 0 0; }
    """

    TOPIC_OPTIONS = [
        ("None — skip scraping", ""),
        ("Python", "python"),
        ("TypeScript / Web", "typescript"),
        ("React", "react"),
        ("Node.js", "node"),
        ("Rust", "rust"),
        ("DevOps", "devops"),
    ]

    def __init__(self, model_name: str = "forgeagent"):
        super().__init__()
        self._model = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="imw"):
            yield Static("Improve Model", classes="title")
            yield Static(f"Add more training data to: {self._model}", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="imw-scroll"):
                yield Static("Learn from your conversations?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=True, id="imw-harvest")
                    yield Static("Yes, use my chat history")
                yield Static("Scrape additional web data?", classes="field-label")
                yield Select(self.TOPIC_OPTIONS, value="", id="imw-topic")
            with Horizontal(id="imw-actions"):
                yield Button("Improve", variant="success", id="imw-go")
                yield Button("Cancel", id="imw-no")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "imw-no":
            self.dismiss(None)
        elif e.button.id == "imw-go":
            topic_sel = self.query_one("#imw-topic", Select)
            topic_val = str(topic_sel.value) if topic_sel.value != Select.BLANK else ""
            self.dismiss({
                "model_name": self._model,
                "harvest_conversations": self.query_one("#imw-harvest", Switch).value,
                "scrape_topic": topic_val or None,
            })


# ══════════════════════════════════════════════════════════════
#  RETRAIN WIZARD — rebuild model from scratch with fresh data
# ══════════════════════════════════════════════════════════════
class RetrainWizard(ModalScreen[dict | None]):
    """Wipe existing training data and rebuild model from scratch."""

    CSS = """
    RetrainWizard { align: center middle; }
    #rtw {
        width: 60; height: 28;
        border: round $warning; background: $surface;
        padding: 1 2;
    }
    #rtw Static.title { text-style: bold; color: $warning; margin: 0 0 1 0; }
    #rtw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #rtw-scroll { height: 1fr; }
    #rtw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #rtw-scroll Select { margin: 0; }
    #rtw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #rtw-actions Button { min-width: 20; margin: 0 1 0 0; height: 3; }
    """

    FOCUS_OPTIONS = [
        ("Python  (FastAPI, Django, ML)", "python"),
        ("Web / Fullstack  (React, Node, TS)", "web"),
        ("Rust  (Tokio, systems)", "rust"),
        ("Go  (microservices, CLIs)", "go"),
        ("DevOps  (Docker, K8s, CI/CD)", "devops"),
        ("General  (all-purpose coding)", "general"),
    ]

    def __init__(self, model_name: str = "forgeagent"):
        super().__init__()
        self._model = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rtw"):
            yield Static("Retrain Model", classes="title")
            yield Static(f"Rebuild '{self._model}' from scratch with fresh data.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="rtw-scroll"):
                yield Static("Focus area for fresh training data", classes="field-label")
                yield Select(self.FOCUS_OPTIONS, value="python", id="rtw-focus")
            with Horizontal(id="rtw-actions"):
                yield Button("Retrain", variant="warning", id="rtw-go")
                yield Button("Cancel", id="rtw-no")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "rtw-no":
            self.dismiss(None)
        elif e.button.id == "rtw-go":
            focus_sel = self.query_one("#rtw-focus", Select)
            self.dismiss({
                "model_name": self._model,
                "focus": str(focus_sel.value) if focus_sel.value != Select.BLANK else "general",
            })


# ══════════════════════════════════════════════════════════════
#  CONTINUE TRAINING WIZARD — add more data and rebuild
# ══════════════════════════════════════════════════════════════
class ContinueTrainWizard(ModalScreen[dict | None]):
    """Add more training data to an existing model and rebuild."""

    CSS = """
    ContinueTrainWizard { align: center middle; }
    #ctw {
        width: 60; height: 32;
        border: round $primary; background: $surface;
        padding: 1 2;
    }
    #ctw Static.title { text-style: bold; color: $primary; margin: 0 0 1 0; }
    #ctw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #ctw-scroll { height: 1fr; }
    #ctw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #ctw-scroll Select { margin: 0; }
    #ctw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #ctw-actions Button { min-width: 20; margin: 0 1 0 0; height: 3; }
    .toggle-row { height: 3; padding: 0 0; }
    .toggle-row Static { padding: 1 1 0 0; }
    """

    TOPIC_OPTIONS = [
        ("None — skip scraping", ""),
        ("Python", "python"),
        ("TypeScript / Web", "typescript"),
        ("React", "react"),
        ("Node.js", "node"),
        ("Rust", "rust"),
        ("DevOps", "devops"),
    ]

    def __init__(self, model_name: str = "forgeagent"):
        super().__init__()
        self._model = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="ctw"):
            yield Static("Continue Training", classes="title")
            yield Static(f"Add more data to '{self._model}' and rebuild.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="ctw-scroll"):
                yield Static("Learn from your conversations?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=True, id="ctw-harvest")
                    yield Static("Yes, use my chat history")
                yield Static("Learn from local codebase?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=True, id="ctw-codebase")
                    yield Static("Yes, scan project files")
                yield Static("Scrape more web data?", classes="field-label")
                yield Select(self.TOPIC_OPTIONS, value="", id="ctw-topic")
                yield Static("Generate more synthetic examples?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=True, id="ctw-synthetic")
                    yield Static("Yes, add tool-use examples")
            with Horizontal(id="ctw-actions"):
                yield Button("Continue Training", variant="success", id="ctw-go")
                yield Button("Cancel", id="ctw-no")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "ctw-no":
            self.dismiss(None)
        elif e.button.id == "ctw-go":
            topic_sel = self.query_one("#ctw-topic", Select)
            topic_val = str(topic_sel.value) if topic_sel.value != Select.BLANK else ""
            self.dismiss({
                "model_name": self._model,
                "harvest_conversations": self.query_one("#ctw-harvest", Switch).value,
                "harvest_codebase": self.query_one("#ctw-codebase", Switch).value,
                "scrape_topic": topic_val or None,
                "add_synthetic": self.query_one("#ctw-synthetic", Switch).value,
            })


# ══════════════════════════════════════════════════════════════
#  FOLDER PICKER
# ══════════════════════════════════════════════════════════════
class FolderPicker(ModalScreen[str | None]):
    """Browse for a folder using a directory tree."""

    CSS = """
    FolderPicker { align: center middle; }
    #fp {
        width: 60; height: 30;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #fp Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #fp-tree { height: 1fr; }
    #fp-selected { color: $success; height: 1; margin: 1 0 0 0; }
    #fp-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #fp-actions Button { min-width: 14; margin: 0 1 0 0; height: 3; }
    """

    def __init__(self, start_path: str = "."):
        super().__init__()
        self._start = start_path
        self._selected: str | None = None

    def compose(self) -> ComposeResult:
        import os
        root = self._start if self._start != "." else os.path.expanduser("~")
        with Vertical(id="fp"):
            yield Static("Select Folder", classes="title")
            yield DirectoryTree(root, id="fp-tree")
            yield Static("", id="fp-selected")
            with Horizontal(id="fp-actions"):
                yield Button("Select", variant="success", id="fp-select")
                yield Button("Cancel", id="fp-cancel")

    def on_directory_tree_directory_selected(self, e: DirectoryTree.DirectorySelected):
        self._selected = str(e.path)
        self.query_one("#fp-selected", Static).update(f"  [green]{self._selected}[/]")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "fp-cancel":
            self.dismiss(None)
        elif e.button.id == "fp-select":
            self.dismiss(self._selected)


# ══════════════════════════════════════════════════════════════
#  DEPLOY WIZARD
# ══════════════════════════════════════════════════════════════
class DeployWizard(ModalScreen[dict | None]):
    """Deploy an agent to a project folder."""

    CSS = """
    DeployWizard { align: center middle; }
    #dw {
        width: 64; height: 32;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #dw Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #dw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #dw-scroll { height: 1fr; }
    #dw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #dw-scroll Input { margin: 0; }
    #dw-scroll Select { margin: 0; }
    #dw-path-row { height: 3; }
    #dw-path-row Input { width: 1fr; }
    #dw-browse { width: 10; height: 3; margin: 0 0 0 1; }
    #dw-detected { color: $success; margin: 0 0 0 1; }
    #dw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #dw-actions Button { min-width: 18; margin: 0 1 0 0; height: 3; }
    """

    TEMPLATES = [
        ("Fullstack (Web / Node / React)", "fullstack"),
        ("Python (ML / FastAPI / Django)", "python"),
        ("Rust (systems programming)", "rust"),
        ("Go (microservices / CLIs)", "go"),
        ("DevOps (Docker / K8s / CI-CD)", "devops"),
        ("Minimal (lightweight)", "minimal"),
        ("Reviewer (code review)", "reviewer"),
        ("Docs (documentation)", "docs"),
    ]

    def __init__(self, model: str = "forgeagent"):
        super().__init__()
        self._model = model

    def compose(self) -> ComposeResult:
        with Vertical(id="dw"):
            yield Static("Deploy Agent", classes="title")
            yield Static("Set up a coding agent in your project folder.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="dw-scroll"):
                yield Static("Project folder path", classes="field-label")
                with Horizontal(id="dw-path-row"):
                    yield Input(placeholder="C:/Projects/myapp", id="dw-path")
                    yield Button("Browse", id="dw-browse")
                yield Static("", id="dw-detected")
                yield Static("Template", classes="field-label")
                yield Select(self.TEMPLATES, value="fullstack", id="dw-tpl")
                yield Static("Agent name (optional)", classes="field-label")
                yield Input(placeholder="auto-generated from folder name", id="dw-name")
                yield Static("Model", classes="field-label")
                yield Input(value=self._model, id="dw-model")
            with Horizontal(id="dw-actions"):
                yield Button("Deploy", variant="success", id="dw-go")
                yield Button("Cancel", id="dw-no")

    def on_mount(self):
        self.query_one("#dw-path", Input).focus()

    def on_input_changed(self, e: Input.Changed):
        if e.input.id == "dw-path":
            path = e.value.strip()
            if path:
                from .automation import detect_project_type
                detected = detect_project_type(path)
                self.query_one("#dw-detected", Static).update(f"  Detected: {detected}")
                # Auto-select template
                tpl_select = self.query_one("#dw-tpl", Select)
                tpl_select.value = detected
            else:
                self.query_one("#dw-detected", Static).update("")

    def _on_folder_picked(self, path: str | None):
        if path:
            inp = self.query_one("#dw-path", Input)
            inp.value = path

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "dw-browse":
            self.app.push_screen(FolderPicker(), callback=self._on_folder_picked)
            return
        if e.button.id == "dw-no":
            self.dismiss(None)
        elif e.button.id == "dw-go":
            from pathlib import Path as P
            path = self.query_one("#dw-path", Input).value.strip()
            tpl_sel = self.query_one("#dw-tpl", Select)
            name = self.query_one("#dw-name", Input).value.strip()
            if not name and path:
                name = P(path).name.lower().replace(" ", "-") or "agent"
            self.dismiss({
                "name": name or "agent",
                "path": path,
                "template": str(tpl_sel.value) if tpl_sel.value != Select.BLANK else "fullstack",
                "model": self.query_one("#dw-model", Input).value.strip() or self._model,
            })


# ══════════════════════════════════════════════════════════════
#  TOOL INPUT MODAL — generic single/multi-field input
# ══════════════════════════════════════════════════════════════
class ToolInputModal(ModalScreen[str | None]):
    """Generic modal that asks for one input field and returns a natural-language message."""

    CSS = """
    ToolInputModal { align: center middle; }
    #tim {
        width: 56; height: auto; max-height: 20;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #tim Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #tim Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #tim Input { margin: 0; }
    #tim-actions { height: auto; margin: 1 0 0 0; }
    #tim-actions Button { min-width: 14; margin: 0 1 0 0; height: 3; }
    """

    def __init__(self, title: str, field_label: str, placeholder: str, message_template: str):
        """
        message_template: format string with {value}, e.g. "Read the file {value}"
        """
        super().__init__()
        self._title = title
        self._field_label = field_label
        self._placeholder = placeholder
        self._template = message_template

    def compose(self) -> ComposeResult:
        with Vertical(id="tim"):
            yield Static(self._title, classes="title")
            yield Static(self._field_label, classes="field-label")
            yield Input(placeholder=self._placeholder, id="tim-input")
            with Horizontal(id="tim-actions"):
                yield Button("Go", variant="success", id="tim-go")
                yield Button("Cancel", id="tim-no")

    def on_mount(self):
        self.query_one("#tim-input", Input).focus()

    def on_input_submitted(self, e: Input.Submitted):
        self._submit()

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "tim-no":
            self.dismiss(None)
        elif e.button.id == "tim-go":
            self._submit()

    def _submit(self):
        value = self.query_one("#tim-input", Input).value.strip()
        if value:
            self.dismiss(self._template.format(value=value))
        else:
            self.dismiss(None)


# ══════════════════════════════════════════════════════════════
#  INFO MODAL — read-only display
# ══════════════════════════════════════════════════════════════
class InfoModal(ModalScreen[None]):
    """Display read-only information in a scrollable view."""

    CSS = """
    InfoModal { align: center middle; }
    #info {
        width: 70; height: 30;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #info Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #info-content { height: 1fr; }
    #info-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #info-actions Button { min-width: 14; height: 3; }
    """

    def __init__(self, title: str, content: str):
        super().__init__()
        self._title = title
        self._content = content

    def compose(self) -> ComposeResult:
        with Vertical(id="info"):
            yield Static(self._title, classes="title")
            yield Rule()
            log = RichLog(id="info-content", wrap=True, markup=True)
            yield log
            with Horizontal(id="info-actions"):
                yield Button("Close", id="info-close")

    def on_mount(self):
        log = self.query_one("#info-content", RichLog)
        for line in self._content.split("\n"):
            log.write(line)

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "info-close":
            self.dismiss(None)


# ══════════════════════════════════════════════════════════════
#  MODEL SELECT WIZARD — switch active model or continue training
# ══════════════════════════════════════════════════════════════
class ModelSelectWizard(ModalScreen[dict | None]):
    """Pick a model to activate or continue training on."""

    CSS = """
    ModelSelectWizard { align: center middle; }
    #msw {
        width: 72; height: 34;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #msw Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #msw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #msw-scroll { height: 1fr; }
    .model-row {
        height: 3; padding: 0 1; margin: 0 0 1 0;
        background: $panel;
    }
    .model-row Static.model-name {
        width: 1fr; padding: 1 0 0 0;
    }
    .model-row Static.model-active {
        width: auto; padding: 1 1 0 0;
        color: $success; text-style: bold;
    }
    .model-row Button {
        width: auto; min-width: 10; height: 3;
        margin: 0 0 0 1;
    }
    #msw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #msw-actions Button { min-width: 14; height: 3; }
    """

    def __init__(self, models: list[dict], current_model: str, profiles: list[dict]):
        super().__init__()
        self._models = models
        self._current = current_model
        self._profile_names = {p["name"] for p in profiles}

    def compose(self) -> ComposeResult:
        with Vertical(id="msw"):
            yield Static("Models", classes="title")
            yield Static("Select a model to use, or continue training it.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="msw-scroll"):
                if not self._models:
                    yield Static("[dim]No models installed. Click AUTO TRAIN to build one.[/]")
                for i, m in enumerate(self._models):
                    name = m["name"]
                    size = m.get("size", "?")
                    is_active = name == self._current
                    has_profile = name in self._profile_names
                    with Horizontal(classes="model-row"):
                        if is_active:
                            yield Static("[green]ACTIVE[/]", classes="model-active")
                        yield Static(f"[bold]{name}[/]  [dim]{size}[/]", classes="model-name")
                        yield Button("Use", id=f"msw-use-{i}", variant="success")
                        if has_profile:
                            yield Button("Train", id=f"msw-train-{i}", variant="primary")
                            yield Button("Retrain", id=f"msw-retrain-{i}", variant="warning")
                        yield Button("Bench", id=f"msw-bench-{i}")
            with Horizontal(id="msw-actions"):
                yield Button("Close", id="msw-close")

    def on_button_pressed(self, e: Button.Pressed):
        bid = e.button.id or ""
        if bid == "msw-close":
            self.dismiss(None)
        elif bid.startswith("msw-use-"):
            idx = int(bid.split("-")[-1])
            if idx < len(self._models):
                self.dismiss({"action": "use", "model": self._models[idx]["name"]})
        elif bid.startswith("msw-train-"):
            idx = int(bid.split("-")[-1])
            if idx < len(self._models):
                self.dismiss({"action": "train", "model": self._models[idx]["name"]})
        elif bid.startswith("msw-retrain-"):
            idx = int(bid.split("-")[-1])
            if idx < len(self._models):
                self.dismiss({"action": "retrain", "model": self._models[idx]["name"]})
        elif bid.startswith("msw-bench-"):
            idx = int(bid.split("-")[-1])
            if idx < len(self._models):
                self.dismiss({"action": "benchmark", "model": self._models[idx]["name"]})
