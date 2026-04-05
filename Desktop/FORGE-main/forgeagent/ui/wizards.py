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
    """One-click model training — build new or refine existing model."""

    INTENSITY_OPTIONS = [
        ("Light  (20 examples, 50 files)", "light"),
        ("Medium  (50 examples, 100 files)", "medium"),
        ("Heavy  (100 examples, 200 files)", "heavy"),
        ("Maximum  (200 examples, 500 files)", "max"),
    ]

    CSS = """
    AutoTrainWizard { align: center middle; }
    #atw {
        width: 62; height: 42;
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

    def __init__(self, installed_models: list[dict] | None = None):
        super().__init__()
        self._installed = installed_models or []

    def compose(self) -> ComposeResult:
        # Build existing model options
        model_options = [("Build New Model", "__new__")]
        for m in self._installed:
            name = m["name"]
            size = m.get("size", "")
            model_options.append((f"Refine: {name}  ({size})", name))

        with Vertical(id="atw"):
            yield Static("Auto Train", classes="title")
            yield Static("Build a new model or refine an existing one.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="atw-scroll"):
                yield Static("Start from", classes="field-label")
                yield Select(model_options, value="__new__", id="atw-existing")
                yield Static("What kind of coding?", classes="field-label")
                yield Select(self.FOCUS_OPTIONS, value="python", id="atw-focus")
                yield Static("Model size (for new models)", classes="field-label")
                yield Select(self.SIZE_OPTIONS, value="balanced", id="atw-size")
                yield Static("Training intensity", classes="field-label")
                yield Select(self.INTENSITY_OPTIONS, value="medium", id="atw-intensity")
                yield Static("Model name (optional)", classes="field-label")
                yield Input(placeholder="auto-generated if blank", id="atw-name")
            with Horizontal(id="atw-actions"):
                yield Button("Start Training", variant="success", id="atw-go")
                yield Button("Cancel", id="atw-no")

    def on_mount(self):
        self.query_one("#atw-existing", Select).focus()

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "atw-no":
            self.dismiss(None)
        elif e.button.id == "atw-go":
            focus_sel = self.query_one("#atw-focus", Select)
            size_sel = self.query_one("#atw-size", Select)
            existing_sel = self.query_one("#atw-existing", Select)
            intensity_sel = self.query_one("#atw-intensity", Select)
            existing = str(existing_sel.value) if existing_sel.value != Select.BLANK else "__new__"
            self.dismiss({
                "focus": str(focus_sel.value) if focus_sel.value != Select.BLANK else "general",
                "size": str(size_sel.value) if size_sel.value != Select.BLANK else "balanced",
                "name": self.query_one("#atw-name", Input).value.strip() or "",
                "existing_model": existing if existing != "__new__" else None,
                "intensity": str(intensity_sel.value) if intensity_sel.value != Select.BLANK else "medium",
            })


# ══════════════════════════════════════════════════════════════
#  IMPROVE MODEL WIZARD
# ══════════════════════════════════════════════════════════════
class ImproveWizard(ModalScreen[dict | None]):
    """Improve an existing model by adding more training data."""

    CSS = """
    ImproveWizard { align: center middle; }
    #imw {
        width: 60; height: 34;
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

    INTENSITY_OPTIONS = [
        ("Light  (20 examples, 50 files)", "light"),
        ("Medium  (50 examples, 100 files)", "medium"),
        ("Heavy  (100 examples, 200 files)", "heavy"),
        ("Maximum  (200 examples, 500 files)", "max"),
    ]

    def __init__(self, model_name: str = "forgeagent", installed_models: list[dict] | None = None):
        super().__init__()
        self._model = model_name
        self._installed = installed_models or []

    def compose(self) -> ComposeResult:
        model_options = []
        option_values = set()
        for m in self._installed:
            name = m["name"]
            size = m.get("size", "")
            model_options.append((f"{name}  ({size})", name))
            option_values.add(name)
        if self._model not in option_values:
            model_options.insert(0, (self._model, self._model))
            option_values.add(self._model)
        if not model_options:
            model_options.append((self._model, self._model))
        default = self._model if self._model in option_values else model_options[0][1]

        with Vertical(id="imw"):
            yield Static("Improve Model", classes="title")
            yield Static("Select a model and add more training data.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="imw-scroll"):
                yield Static("Which model to improve?", classes="field-label")
                yield Select(model_options, value=default, id="imw-model")
                yield Static("Training intensity", classes="field-label")
                yield Select(self.INTENSITY_OPTIONS, value="medium", id="imw-intensity")
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
            model_sel = self.query_one("#imw-model", Select)
            topic_sel = self.query_one("#imw-topic", Select)
            intensity_sel = self.query_one("#imw-intensity", Select)
            model_val = str(model_sel.value) if model_sel.value != Select.BLANK else self._model
            topic_val = str(topic_sel.value) if topic_sel.value != Select.BLANK else ""
            self.dismiss({
                "model_name": model_val,
                "harvest_conversations": self.query_one("#imw-harvest", Switch).value,
                "scrape_topic": topic_val or None,
                "intensity": str(intensity_sel.value) if intensity_sel.value != Select.BLANK else "medium",
            })


# ══════════════════════════════════════════════════════════════
#  COMPETITION WIZARD — VS Claude Code with folder picker
# ══════════════════════════════════════════════════════════════
class CompetitionWizard(ModalScreen[dict | None]):
    """Pick a project folder to run head-to-head competition with Claude Code."""

    CSS = """
    CompetitionWizard { align: center middle; }
    #cmpw {
        width: 62; height: 24;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #cmpw Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #cmpw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #cmpw-scroll { height: 1fr; }
    #cmpw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #cmpw-scroll Input { margin: 0; }
    #cmpw-path-row { height: 3; }
    #cmpw-path-row Input { width: 1fr; }
    #cmpw-browse { width: 10; height: 3; margin: 0 0 0 1; }
    #cmpw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #cmpw-actions Button { min-width: 18; margin: 0 1 0 0; height: 3; }
    """

    def __init__(self, model_name: str = "forgeagent"):
        super().__init__()
        self._model = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="cmpw"):
            yield Static("VS Claude Code", classes="title")
            yield Static(f"Run {self._model} head-to-head against Claude Code CLI.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="cmpw-scroll"):
                yield Static("Project folder for competition", classes="field-label")
                with Horizontal(id="cmpw-path-row"):
                    yield Input(placeholder="C:/Projects/myapp  (or . for current)", id="cmpw-path", value=".")
                    yield Button("Browse", id="cmpw-browse")
            with Horizontal(id="cmpw-actions"):
                yield Button("Start Competition", variant="success", id="cmpw-go")
                yield Button("Cancel", id="cmpw-no")

    def on_mount(self):
        self.query_one("#cmpw-path", Input).focus()

    def _on_folder_picked(self, path: str | None):
        if path:
            self.query_one("#cmpw-path", Input).value = path

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "cmpw-browse":
            self.app.push_screen(FolderPicker(), callback=self._on_folder_picked)
            return
        if e.button.id == "cmpw-no":
            self.dismiss(None)
        elif e.button.id == "cmpw-go":
            path = self.query_one("#cmpw-path", Input).value.strip() or "."
            self.dismiss({"path": path})


# ══════════════════════════════════════════════════════════════
#  SHADOW LEARN WIZARD — watch Claude Code and learn
# ══════════════════════════════════════════════════════════════
class ShadowLearnWizard(ModalScreen[dict | None]):
    """Deploy Claude Code into a project folder and learn from its work."""

    CSS = """
    ShadowLearnWizard { align: center middle; }
    #slw {
        width: 62; height: 28;
        border: round $warning; background: $surface;
        padding: 1 2;
    }
    #slw Static.title { text-style: bold; color: $warning; margin: 0 0 1 0; }
    #slw Static.subtitle { color: $text-muted; margin: 0 0 1 0; }
    #slw-scroll { height: 1fr; }
    #slw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #slw-scroll Input { margin: 0; }
    #slw-scroll Select { margin: 0; }
    #slw-path-row { height: 3; }
    #slw-path-row Input { width: 1fr; }
    #slw-browse { width: 10; height: 3; margin: 0 0 0 1; }
    #slw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #slw-actions Button { min-width: 18; margin: 0 1 0 0; height: 3; }
    """

    TASK_SETS = [
        ("Full Review (10 tasks — recommended)", "full"),
        ("Deep Dive (20 tasks — thorough)", "deep"),
        ("Quick (3 tasks — code review only)", "quick"),
        ("Architecture (3 tasks — structure focused)", "arch"),
        ("Testing (3 tasks — write tests)", "test"),
    ]

    PASS_OPTIONS = [
        ("1 pass  (quick)", "1"),
        ("3 passes  (recommended)", "3"),
        ("5 passes  (thorough)", "5"),
        ("10 passes  (maximum learning)", "10"),
    ]

    def __init__(self, model_name: str = "forgeagent"):
        super().__init__()
        self._model = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="slw"):
            yield Static("Shadow Learning", classes="title")
            yield Static(f"Claude Code works on a project. {self._model} learns.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="slw-scroll"):
                yield Static("Project folder", classes="field-label")
                with Horizontal(id="slw-path-row"):
                    yield Input(placeholder="C:/Projects/myapp", id="slw-path")
                    yield Button("Browse", id="slw-browse")
                yield Static("What should Claude demonstrate?", classes="field-label")
                yield Select(self.TASK_SETS, value="full", id="slw-tasks")
                yield Static("How many learning passes?", classes="field-label")
                yield Select(self.PASS_OPTIONS, value="1", id="slw-passes")
            with Horizontal(id="slw-actions"):
                yield Button("Start Learning", variant="warning", id="slw-go")
                yield Button("Cancel", id="slw-no")

    def on_mount(self):
        self.query_one("#slw-path", Input).focus()

    def _on_folder_picked(self, path: str | None):
        if path:
            self.query_one("#slw-path", Input).value = path

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "slw-browse":
            self.app.push_screen(FolderPicker(), callback=self._on_folder_picked)
            return
        if e.button.id == "slw-no":
            self.dismiss(None)
        elif e.button.id == "slw-go":
            path = self.query_one("#slw-path", Input).value.strip()
            task_sel = self.query_one("#slw-tasks", Select)
            pass_sel = self.query_one("#slw-passes", Select)
            task_set = str(task_sel.value) if task_sel.value != Select.BLANK else "full"
            passes = int(str(pass_sel.value)) if pass_sel.value != Select.BLANK else 1
            if not path:
                return
            self.dismiss({"path": path, "task_set": task_set, "passes": passes})


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
#  LAUNCH AGENTS WIZARD — select 1-6 models to launch as terminal agents
# ══════════════════════════════════════════════════════════════
class LaunchAgentsWizard(ModalScreen[dict | None]):
    """Select trained models and launch them as terminal coding agents."""

    CSS = """
    LaunchAgentsWizard { align: center middle; }
    #law {
        width: 68; height: 38;
        border: round #00e5ff; background: #111822;
        padding: 1 2;
    }
    #law Static.title { text-style: bold; color: #00e5ff; margin: 0 0 1 0; }
    #law Static.subtitle { color: #5c6b7a; margin: 0 0 1 0; }
    #law-scroll { height: 1fr; }
    #law-scroll Static.field-label { color: #5c6b7a; margin: 1 0 0 0; }
    #law-scroll Input { margin: 0; }
    #law-scroll Select { margin: 0; }
    #law-path-row { height: 3; }
    #law-path-row Input { width: 1fr; }
    #law-browse { width: 10; height: 3; margin: 0 0 0 1; }
    #law-detected { color: #00e676; margin: 0 0 0 1; }
    #law-count { color: #00e5ff; text-style: bold; margin: 1 0 0 0; height: 1; }
    .model-check-row {
        height: 2; padding: 0 1; margin: 0;
    }
    .model-check-row Switch { width: 8; }
    .model-check-row Static {
        padding: 0 0 0 1; width: 1fr;
    }
    #law-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #law-actions Button { min-width: 18; margin: 0 1 0 0; height: 3; }
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

    def __init__(self, installed_models: list[dict] | None = None):
        super().__init__()
        self._installed = installed_models or []

    def compose(self) -> ComposeResult:
        with Vertical(id="law"):
            yield Static("LAUNCH AGENTS", classes="title")
            yield Static("Select 1-6 trained models to deploy as terminal coding agents.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="law-scroll"):
                yield Static("Project folder", classes="field-label")
                with Horizontal(id="law-path-row"):
                    yield Input(placeholder="C:/Projects/myapp", id="law-path")
                    yield Button("Browse", id="law-browse")
                yield Static("", id="law-detected")
                yield Static("Template", classes="field-label")
                yield Select(self.TEMPLATES, value="fullstack", id="law-tpl")
                yield Rule()
                yield Static("Select models to launch (1-6)", classes="field-label")
                yield Static("Selected: 0/6", id="law-count")
                if not self._installed:
                    yield Static("[dim]No models installed. Train one first with AUTO TRAIN.[/]")
                for i, m in enumerate(self._installed[:12]):
                    name = m["name"]
                    size = m.get("size", "")
                    with Horizontal(classes="model-check-row"):
                        yield Switch(value=(i == 0), id=f"law-sw-{i}")
                        yield Static(f"[bold]{name}[/]  [dim]{size}[/]", id=f"law-label-{i}")
            with Horizontal(id="law-actions"):
                yield Button("LAUNCH", variant="success", id="law-go")
                yield Button("Cancel", id="law-no")

    def on_mount(self):
        self.query_one("#law-path", Input).focus()
        self._update_count()

    def on_switch_changed(self, e: Switch.Changed):
        if str(e.switch.id or "").startswith("law-sw-"):
            self._update_count()

    def _update_count(self):
        count = self._count_selected()
        label = self.query_one("#law-count", Static)
        if count > 6:
            label.update(f"[red]Selected: {count}/6 (max 6!)[/]")
        elif count == 0:
            label.update(f"[#ffd740]Selected: 0/6 (select at least 1)[/]")
        else:
            label.update(f"[#00e5ff]Selected: {count}/6[/]")

    def _count_selected(self) -> int:
        count = 0
        for i in range(len(self._installed[:12])):
            try:
                sw = self.query_one(f"#law-sw-{i}", Switch)
                if sw.value:
                    count += 1
            except Exception:
                pass
        return count

    def _get_selected_models(self) -> list[str]:
        selected = []
        for i, m in enumerate(self._installed[:12]):
            try:
                sw = self.query_one(f"#law-sw-{i}", Switch)
                if sw.value:
                    selected.append(m["name"])
            except Exception:
                pass
        return selected[:6]

    def on_input_changed(self, e: Input.Changed):
        if e.input.id == "law-path":
            path = e.value.strip()
            if path:
                from .automation import detect_project_type
                detected = detect_project_type(path)
                self.query_one("#law-detected", Static).update(f"  [#00e676]Detected: {detected}[/]")
                try:
                    tpl_select = self.query_one("#law-tpl", Select)
                    tpl_select.value = detected
                except Exception:
                    pass
            else:
                self.query_one("#law-detected", Static).update("")

    def _on_folder_picked(self, path: str | None):
        if path:
            self.query_one("#law-path", Input).value = path

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "law-browse":
            self.app.push_screen(FolderPicker(), callback=self._on_folder_picked)
            return
        if e.button.id == "law-no":
            self.dismiss(None)
        elif e.button.id == "law-go":
            path = self.query_one("#law-path", Input).value.strip()
            models = self._get_selected_models()
            if not path:
                return
            if not models:
                return
            tpl_sel = self.query_one("#law-tpl", Select)
            self.dismiss({
                "path": path,
                "models": models,
                "template": str(tpl_sel.value) if tpl_sel.value != Select.BLANK else "fullstack",
            })


# Keep DeployWizard as alias for backward compatibility
DeployWizard = LaunchAgentsWizard


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

    def compose(self) -> ComposeResult:
        with Vertical(id="msw"):
            yield Static("Models", classes="title")
            yield Static("Select a model to use, train, or benchmark.", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="msw-scroll"):
                if not self._models:
                    yield Static("[dim]No models installed. Click AUTO TRAIN to build one.[/]")
                for i, m in enumerate(self._models):
                    name = m["name"]
                    size = m.get("size", "?")
                    is_active = name == self._current
                    with Horizontal(classes="model-row"):
                        if is_active:
                            yield Static("[green]ACTIVE[/]", classes="model-active")
                        yield Static(f"[bold]{name}[/]  [dim]{size}[/]", classes="model-name")
                        yield Button("Use", id=f"msw-use-{i}", variant="success")
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


# ══════════════════════════════════════════════════════════════
#  PROJECT WIZARD — manage deployed agent in a project
# ══════════════════════════════════════════════════════════════
class ProjectWizard(ModalScreen[dict | None]):
    """Manage a deployed agent — on/off, git, logs, settings."""

    CSS = """
    ProjectWizard { align: center middle; }
    #pw {
        width: 68; height: 36;
        border: round $accent; background: $surface;
        padding: 1 2;
    }
    #pw Static.title { text-style: bold; color: $accent; margin: 0 0 1 0; }
    #pw Static.subtitle { color: $text-muted; margin: 0 0 0 0; }
    #pw-scroll { height: 1fr; }
    #pw-scroll Static.field-label { color: $text-muted; margin: 1 0 0 0; }
    #pw-scroll Input { margin: 0; }
    .toggle-row { height: 3; padding: 0 0; }
    .toggle-row Static { padding: 1 1 0 0; }
    .action-row { height: 3; margin: 0 0 1 0; }
    .action-row Button { min-width: 14; margin: 0 1 0 0; height: 3; }
    #pw-actions { height: auto; dock: bottom; margin: 1 0 0 0; }
    #pw-actions Button { min-width: 14; margin: 0 1 0 0; height: 3; }
    """

    def __init__(self, agent: dict, profile: dict | None = None):
        super().__init__()
        self._agent = agent
        self._profile = profile or {}
        self._git = self._profile.get("git", {})

    def compose(self) -> ComposeResult:
        name = self._agent.get("name", "agent")
        status = self._profile.get("status", self._agent.get("status", "stopped"))
        is_running = status == "running"
        path = self._agent.get("projectPath", "")

        with Vertical(id="pw"):
            yield Static(f"Project: {name}", classes="title")
            yield Static(f"[dim]{path}[/]", classes="subtitle")
            yield Rule()
            with VerticalScroll(id="pw-scroll"):
                # Status & control
                yield Static("Agent Control", classes="field-label")
                with Horizontal(classes="action-row"):
                    if is_running:
                        yield Button("Stop Agent", variant="error", id="pw-stop")
                    else:
                        yield Button("Start Agent", variant="success", id="pw-start")
                    yield Button("Launch Terminal", id="pw-launch")

                # Git
                yield Static("Git", classes="field-label")
                with Horizontal(classes="action-row"):
                    yield Button("Status", id="pw-git-status")
                    yield Button("Commit", id="pw-git-commit")
                    yield Button("Push", id="pw-git-push")
                    yield Button("Log", id="pw-git-log")

                yield Static("Git remote", classes="field-label")
                yield Input(value=self._git.get("remote", "origin"), id="pw-remote")
                yield Static("Git branch", classes="field-label")
                yield Input(value=self._git.get("branch", "main"), id="pw-branch")

                yield Static("Auto-commit after agent tasks?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=self._git.get("autoCommit", False), id="pw-auto-commit")
                    yield Static("Auto-commit")
                yield Static("Auto-push after commits?", classes="field-label")
                with Horizontal(classes="toggle-row"):
                    yield Switch(value=self._git.get("autoPush", False), id="pw-auto-push")
                    yield Static("Auto-push")

                # Logs
                yield Static("Logs", classes="field-label")
                with Horizontal(classes="action-row"):
                    yield Button("View Logs", id="pw-logs")
                    yield Button("Clear Logs", id="pw-clear-logs")

            with Horizontal(id="pw-actions"):
                yield Button("Save Settings", variant="success", id="pw-save")
                yield Button("Close", id="pw-close")

    def on_button_pressed(self, e: Button.Pressed):
        bid = e.button.id or ""
        if bid == "pw-close":
            self.dismiss(None)
        elif bid == "pw-save":
            self.dismiss({
                "action": "save_settings",
                "git": {
                    "remote": self.query_one("#pw-remote", Input).value.strip() or "origin",
                    "branch": self.query_one("#pw-branch", Input).value.strip() or "main",
                    "autoCommit": self.query_one("#pw-auto-commit", Switch).value,
                    "autoPush": self.query_one("#pw-auto-push", Switch).value,
                },
            })
        elif bid == "pw-start":
            self.dismiss({"action": "start"})
        elif bid == "pw-stop":
            self.dismiss({"action": "stop"})
        elif bid == "pw-launch":
            self.dismiss({"action": "launch"})
        elif bid == "pw-git-status":
            self.dismiss({"action": "git_status"})
        elif bid == "pw-git-commit":
            self.dismiss({"action": "git_commit"})
        elif bid == "pw-git-push":
            self.dismiss({"action": "git_push"})
        elif bid == "pw-git-log":
            self.dismiss({"action": "git_log"})
        elif bid == "pw-logs":
            self.dismiss({"action": "view_logs"})
        elif bid == "pw-clear-logs":
            self.dismiss({"action": "clear_logs"})
