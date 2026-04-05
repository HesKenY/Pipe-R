"""Agent instruction system — generates and updates AGENT.md for deployed agents.

Scans the target project, matches its framework/stack, and writes instructions
that agents read on startup to know what to do and how to work.
Tasks are appended and agents check them automatically.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime


# ── Framework detection ──────────────────────────────────────
FRAMEWORK_SIGNATURES = {
    "nextjs": {
        "files": ["next.config.js", "next.config.ts", "next.config.mjs"],
        "package_keys": ["next"],
        "label": "Next.js",
        "instructions": [
            "This is a Next.js project. Use App Router conventions (app/ directory).",
            "Server Components are default. Use 'use client' only when needed.",
            "API routes go in app/api/. Use route.ts with GET/POST exports.",
            "Run `npm run dev` for development, `npm run build` to check for errors.",
        ],
    },
    "react": {
        "files": ["src/App.tsx", "src/App.jsx", "src/index.tsx"],
        "package_keys": ["react", "react-dom"],
        "label": "React",
        "instructions": [
            "This is a React project. Use functional components and hooks.",
            "Keep components small and focused. Extract shared logic into custom hooks.",
            "Run `npm start` or `npm run dev` for development.",
        ],
    },
    "fastapi": {
        "files": ["main.py"],
        "package_keys": ["fastapi", "uvicorn"],
        "label": "FastAPI",
        "instructions": [
            "This is a FastAPI project. Use async def for route handlers.",
            "Use Pydantic models for request/response validation.",
            "Run with `uvicorn main:app --reload` for development.",
        ],
    },
    "flask": {
        "files": ["app.py", "wsgi.py"],
        "package_keys": ["flask"],
        "label": "Flask",
        "instructions": [
            "This is a Flask project. Use blueprints for organization.",
            "Run with `flask run` or `python app.py` for development.",
        ],
    },
    "django": {
        "files": ["manage.py", "settings.py"],
        "package_keys": ["django"],
        "label": "Django",
        "instructions": [
            "This is a Django project. Follow Django conventions.",
            "Use `python manage.py runserver` for development.",
            "Run migrations with `python manage.py migrate`.",
        ],
    },
    "express": {
        "files": ["server.js", "server.ts", "index.js"],
        "package_keys": ["express"],
        "label": "Express.js",
        "instructions": [
            "This is an Express.js project. Use middleware pattern.",
            "Keep routes in separate files. Use error-handling middleware.",
        ],
    },
    "rust": {
        "files": ["Cargo.toml", "src/main.rs", "src/lib.rs"],
        "package_keys": [],
        "label": "Rust",
        "instructions": [
            "This is a Rust project. Run `cargo check` before committing.",
            "Use `cargo test` to run tests. Follow clippy suggestions.",
        ],
    },
    "go": {
        "files": ["go.mod", "main.go"],
        "package_keys": [],
        "label": "Go",
        "instructions": [
            "This is a Go project. Run `go vet` and `go test ./...` before committing.",
            "Follow standard Go project layout.",
        ],
    },
    "python_general": {
        "files": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"],
        "package_keys": [],
        "label": "Python",
        "instructions": [
            "This is a Python project. Follow PEP 8 style.",
            "Use type hints. Run tests with `pytest`.",
            "Install dependencies: `pip install -r requirements.txt` or `pip install -e .`",
        ],
    },
    "forgeagent": {
        "files": ["forgeagent/__main__.py", "forgeagent/ui/tui.py"],
        "package_keys": ["textual", "rich", "httpx"],
        "label": "ForgeAgent (this project)",
        "instructions": [
            "This is ForgeAgent — a local AI coding agent hub built with Python/Textual.",
            "Main TUI: forgeagent/ui/tui.py. Wizards: forgeagent/ui/wizards.py.",
            "Training pipelines: forgeagent/ui/automation.py.",
            "Tools: forgeagent/tools/registry.py (12 built-in tools).",
            "Deploy system: forgeagent/deploy/agent_deployer.py.",
            "Entry point: forgeagent/__main__.py. Config: forgeagent/config.py.",
            "Test with: python -m forgeagent (TUI) or python -m forgeagent --agent (CLI).",
            "Dependencies: rich, textual, httpx, click, python-dotenv, pydantic.",
        ],
    },
}


def detect_frameworks(project_path: str) -> list[dict]:
    """Detect which frameworks/stacks are present in the project."""
    pp = Path(project_path)
    detected = []

    # Check files
    for fw_id, fw in FRAMEWORK_SIGNATURES.items():
        for sig_file in fw["files"]:
            if (pp / sig_file).exists():
                detected.append({"id": fw_id, **fw})
                break

    # Check package.json dependencies
    pkg_json = pp / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            all_deps = set()
            for key in ("dependencies", "devDependencies"):
                all_deps.update(pkg.get(key, {}).keys())
            for fw_id, fw in FRAMEWORK_SIGNATURES.items():
                if fw_id not in [d["id"] for d in detected]:
                    if any(pk in all_deps for pk in fw["package_keys"]):
                        detected.append({"id": fw_id, **fw})
        except Exception:
            pass

    # Check requirements.txt / pyproject.toml
    for req_file in ["requirements.txt", "pyproject.toml"]:
        req_path = pp / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8").lower()
                for fw_id, fw in FRAMEWORK_SIGNATURES.items():
                    if fw_id not in [d["id"] for d in detected]:
                        if any(pk in content for pk in fw["package_keys"]):
                            detected.append({"id": fw_id, **fw})
            except Exception:
                pass

    return detected


def scan_project_structure(project_path: str) -> dict:
    """Scan project to build a structural summary."""
    pp = Path(project_path)
    info = {
        "path": str(pp),
        "name": pp.name,
        "files": [],
        "dirs": [],
        "entry_points": [],
        "config_files": [],
        "test_files": [],
        "total_files": 0,
    }

    skip = {".git", "node_modules", "__pycache__", ".next", "dist", "build",
            ".forgeagent", ".memory", "venv", ".venv", "env", ".env"}

    for entry in sorted(pp.iterdir()):
        if entry.name.startswith(".") and entry.name not in (".env.example",):
            if entry.name not in (".gitignore",):
                continue
        if entry.name in skip:
            continue

        if entry.is_dir():
            info["dirs"].append(entry.name)
        elif entry.is_file():
            info["files"].append(entry.name)
            # Categorize
            name_lower = entry.name.lower()
            if name_lower in ("main.py", "app.py", "index.ts", "index.js", "server.ts", "server.js", "main.go", "main.rs"):
                info["entry_points"].append(entry.name)
            if name_lower.startswith("test_") or name_lower.endswith("_test.py") or name_lower.endswith(".test.ts"):
                info["test_files"].append(entry.name)
            if name_lower in ("package.json", "pyproject.toml", "cargo.toml", "go.mod", "tsconfig.json",
                              "requirements.txt", ".env.example", "docker-compose.yml", "dockerfile"):
                info["config_files"].append(entry.name)

    # Count total source files
    count = 0
    for fp in pp.rglob("*"):
        if fp.is_file() and not any(s in fp.parts for s in skip):
            count += 1
    info["total_files"] = min(count, 9999)

    return info


def generate_agent_instructions(project_path: str, agent_name: str = "",
                                 model_name: str = "", tasks: list[str] | None = None) -> str:
    """Generate the full AGENT.md instruction file for a deployed agent."""
    pp = Path(project_path)
    frameworks = detect_frameworks(project_path)
    structure = scan_project_structure(project_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []

    # Header
    lines.append(f"# Agent Instructions — {structure['name']}")
    lines.append(f"")
    lines.append(f"Generated: {now}")
    if agent_name:
        lines.append(f"Agent: {agent_name}")
    if model_name:
        lines.append(f"Model: {model_name}")
    lines.append(f"Project: {pp}")
    lines.append(f"")

    # Framework instructions
    lines.append(f"## Framework")
    if frameworks:
        for fw in frameworks:
            lines.append(f"")
            lines.append(f"### {fw['label']}")
            for inst in fw["instructions"]:
                lines.append(f"- {inst}")
    else:
        lines.append(f"- No specific framework detected. Use general best practices.")
    lines.append(f"")

    # Project structure
    lines.append(f"## Project Structure")
    lines.append(f"- Total files: {structure['total_files']}")
    if structure["dirs"]:
        lines.append(f"- Directories: {', '.join(structure['dirs'][:15])}")
    if structure["entry_points"]:
        lines.append(f"- Entry points: {', '.join(structure['entry_points'])}")
    if structure["config_files"]:
        lines.append(f"- Config: {', '.join(structure['config_files'])}")
    if structure["test_files"]:
        lines.append(f"- Tests: {', '.join(structure['test_files'])}")
    lines.append(f"")

    # Rules
    lines.append(f"## Rules")
    lines.append(f"- Read files before modifying them.")
    lines.append(f"- Run tests after making changes.")
    lines.append(f"- Keep changes focused — one task at a time.")
    lines.append(f"- Use existing patterns and conventions from the codebase.")
    lines.append(f"- Do not delete or overwrite files without reading them first.")
    lines.append(f"- Commit with clear messages describing what changed and why.")
    lines.append(f"")
    lines.append(f"## Completion Protocol")
    lines.append(f"When ALL tasks above are completed:")
    lines.append(f"1. Run any tests to verify nothing is broken.")
    lines.append(f"2. Create a timestamped zip of the entire project into the Outputs/ folder:")
    lines.append(f'   - Command: `python -c "import shutil,datetime;shutil.make_archive(\'Outputs/build-\'+datetime.datetime.now().strftime(\'%Y%m%d-%H%M%S\'),\'zip\',\'.\')"` ')
    lines.append(f"3. Report which tasks were completed and any issues found.")
    lines.append(f"4. Wait for new instructions.")
    lines.append(f"")

    # Tasks
    lines.append(f"## Tasks")
    lines.append(f"")
    if tasks:
        for i, task in enumerate(tasks, 1):
            lines.append(f"- [ ] {task}")
    else:
        lines.append(f"- [ ] Read the project structure and understand the codebase")
        lines.append(f"- [ ] Identify any bugs or issues")
        lines.append(f"- [ ] Check for missing tests and add them")
        lines.append(f"- [ ] Review code quality and suggest improvements")
    lines.append(f"")
    lines.append(f"<!-- Add new tasks above this line. Agents check this section on each prompt. -->")
    lines.append(f"")

    return "\n".join(lines)


def write_agent_instructions(project_path: str, agent_name: str = "",
                              model_name: str = "", tasks: list[str] | None = None) -> str:
    """Generate and write AGENT.md to the project's .forgeagent/ folder."""
    pp = Path(project_path)
    agent_dir = pp / ".forgeagent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    content = generate_agent_instructions(project_path, agent_name, model_name, tasks)
    agent_md = agent_dir / "AGENT.md"
    agent_md.write_text(content, encoding="utf-8")
    return str(agent_md)


def add_task(project_path: str, task: str) -> bool:
    """Append a task to the AGENT.md task list."""
    agent_md = Path(project_path) / ".forgeagent" / "AGENT.md"
    if not agent_md.exists():
        return False

    content = agent_md.read_text(encoding="utf-8")
    marker = "<!-- Add new tasks above this line."
    if marker in content:
        content = content.replace(marker, f"- [ ] {task}\n{marker}")
    else:
        content += f"\n- [ ] {task}\n"

    agent_md.write_text(content, encoding="utf-8")
    return True


def complete_task(project_path: str, task_substring: str) -> bool:
    """Mark a task as done in AGENT.md by matching text."""
    agent_md = Path(project_path) / ".forgeagent" / "AGENT.md"
    if not agent_md.exists():
        return False

    content = agent_md.read_text(encoding="utf-8")
    lines = content.split("\n")
    found = False
    for i, line in enumerate(lines):
        if "- [ ]" in line and task_substring.lower() in line.lower():
            lines[i] = line.replace("- [ ]", "- [x]")
            found = True
            break

    if found:
        agent_md.write_text("\n".join(lines), encoding="utf-8")
    return found


def get_pending_tasks(project_path: str) -> list[str]:
    """Read all uncompleted tasks from AGENT.md."""
    agent_md = Path(project_path) / ".forgeagent" / "AGENT.md"
    if not agent_md.exists():
        return []

    tasks = []
    for line in agent_md.read_text(encoding="utf-8").split("\n"):
        if "- [ ]" in line:
            task = line.replace("- [ ]", "").strip()
            if task:
                tasks.append(task)
    return tasks


def get_completed_tasks(project_path: str) -> list[str]:
    """Read all completed tasks from AGENT.md."""
    agent_md = Path(project_path) / ".forgeagent" / "AGENT.md"
    if not agent_md.exists():
        return []

    tasks = []
    for line in agent_md.read_text(encoding="utf-8").split("\n"):
        if "- [x]" in line:
            task = line.replace("- [x]", "").strip()
            if task:
                tasks.append(task)
    return tasks
