"""Iteration engine — generates next-build instructions, harvests learning, maintains agent memory.

This is the brain of the development loop:
1. Analyze current codebase state
2. Generate next iteration tasks (what to build/fix/improve)
3. After agents complete tasks, harvest their work as training data
4. Update persistent agent memory with what was learned
5. Feed improvements back into models
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime
from ..deploy.agent_instructions import (
    write_agent_instructions, get_pending_tasks, get_completed_tasks,
    detect_frameworks, scan_project_structure,
)
from ..training.dataset_manager import DatasetManager, TrainingExample, _uid


class IterationEngine:
    """Manages the build-test-learn cycle."""

    def __init__(self, project_path: str, memory_dir: str):
        self.project_path = Path(project_path).resolve()
        self.memory_dir = Path(memory_dir)
        self.forge_dir = self.project_path / ".forgeagent"
        self.forge_dir.mkdir(parents=True, exist_ok=True)
        self.iterations_file = self.forge_dir / "iterations.json"
        self.agent_memory_file = self.forge_dir / "agent_memory.md"

    # ── Iteration history ────────────────────────
    def _load_iterations(self) -> list[dict]:
        if self.iterations_file.exists():
            try:
                return json.loads(self.iterations_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_iteration(self, iteration: dict):
        history = self._load_iterations()
        history.append(iteration)
        # Keep last 50
        if len(history) > 50:
            history = history[-50:]
        self.iterations_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def get_iteration_count(self) -> int:
        return len(self._load_iterations())

    # ── Persistent agent memory ──────────────────
    def read_agent_memory(self) -> str:
        if self.agent_memory_file.exists():
            return self.agent_memory_file.read_text(encoding="utf-8")
        return ""

    def append_agent_memory(self, section: str, content: str):
        """Append to persistent agent memory that carries across sessions."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## {section} — {ts}\n{content}\n"
        if not self.agent_memory_file.exists():
            self.agent_memory_file.write_text(
                f"# Agent Memory — {self.project_path.name}\n"
                f"Persistent memory across all iterations and sessions.\n",
                encoding="utf-8",
            )
        with open(self.agent_memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

    # ── Generate next iteration tasks ────────────
    def generate_iteration_tasks(self, user_instructions: str = "",
                                  focus: str = "features") -> list[str]:
        """Analyze the project and generate the next batch of development tasks.

        Args:
            user_instructions: Custom instructions from the user (from phone/chat)
            focus: "features", "bugs", "tests", "polish", "refactor"
        """
        structure = scan_project_structure(str(self.project_path))
        frameworks = detect_frameworks(str(self.project_path))
        prev_iterations = self._load_iterations()
        completed_ever = []
        for it in prev_iterations:
            completed_ever.extend(it.get("completed_tasks", []))
        agent_memory = self.read_agent_memory()

        tasks = []

        # Add user instructions first (highest priority)
        if user_instructions:
            for line in user_instructions.strip().split("\n"):
                line = line.strip().lstrip("-").lstrip("*").lstrip("0123456789.").strip()
                if line and len(line) > 5:
                    tasks.append(line)

        # Auto-generate tasks based on focus
        if focus == "features" or not tasks:
            tasks.extend(self._generate_feature_tasks(structure, frameworks, completed_ever))
        if focus == "bugs":
            tasks.extend(self._generate_bug_tasks(structure))
        if focus == "tests":
            tasks.extend(self._generate_test_tasks(structure))
        if focus == "polish":
            tasks.extend(self._generate_polish_tasks(structure))
        if focus == "refactor":
            tasks.extend(self._generate_refactor_tasks(structure))

        # Deduplicate against previous iterations
        completed_lower = {t.lower()[:50] for t in completed_ever}
        tasks = [t for t in tasks if t.lower()[:50] not in completed_lower]

        return tasks[:20]  # Cap at 20 per iteration

    def _generate_feature_tasks(self, structure: dict, frameworks: list, completed: list) -> list[str]:
        """Generate feature development tasks based on project state."""
        tasks = []
        dirs = set(structure.get("dirs", []))
        files = set(structure.get("files", []))

        # Missing standard files
        if "tests" not in dirs and "test" not in dirs:
            tasks.append("Create a tests/ directory with test files for the core modules. Use pytest.")
        if ".gitignore" not in files:
            tasks.append("Create a .gitignore file appropriate for this project type.")
        if "README.md" not in files:
            tasks.append("Write a comprehensive README.md with setup instructions and feature list.")
        if "Dockerfile" not in files and any(f.get("id") in ("fastapi", "flask", "express") for f in frameworks):
            tasks.append("Create a Dockerfile for containerized deployment.")

        # Framework-specific features
        for fw in frameworks:
            fid = fw.get("id", "")
            if fid == "forgeagent":
                tasks.extend([
                    "Add a /history command that shows previous iteration results with scores",
                    "Add agent memory display to the remote dashboard — show what agents have learned",
                    "Add a batch file import: read all .jsonl from datasets/import/ and train in one click",
                    "Improve the team_cli.py — add a /split command that divides a big task among agents automatically",
                ])

        # General improvement tasks
        tasks.extend([
            "Read all source files and identify any functions missing error handling. Add try/except where needed.",
            "Find any hardcoded values that should be configurable. Move them to config or environment variables.",
            "Add logging to key operations that currently have none.",
        ])

        return tasks

    def _generate_bug_tasks(self, structure: dict) -> list[str]:
        return [
            "Search all source files for common bug patterns: bare except, mutable default args, unclosed files. Fix them.",
            "Run any existing tests and fix all failures.",
            "Check all file I/O operations for missing encoding parameters. Add encoding='utf-8' where missing.",
            "Find all TODO and FIXME comments in the codebase and resolve them.",
        ]

    def _generate_test_tasks(self, structure: dict) -> list[str]:
        return [
            "Write unit tests for all public functions that don't have tests yet. Aim for 80% coverage.",
            "Add edge case tests: empty inputs, None values, very large inputs, unicode strings.",
            "Write integration tests that test full workflows end-to-end.",
            "Add a test configuration (conftest.py) with useful fixtures.",
        ]

    def _generate_polish_tasks(self, structure: dict) -> list[str]:
        return [
            "Add type hints to all functions missing them.",
            "Add docstrings to all public functions and classes.",
            "Standardize error messages across all modules — use consistent format.",
            "Review all user-facing text for clarity and consistency.",
        ]

    def _generate_refactor_tasks(self, structure: dict) -> list[str]:
        return [
            "Identify duplicate code across files and extract into shared utilities.",
            "Find functions longer than 50 lines and split them into smaller focused functions.",
            "Review import structure — remove unused imports, organize into groups.",
            "Simplify any overly complex conditional logic.",
        ]

    # ── Write tasks to AGENT.md ──────────────────
    def write_iteration(self, tasks: list[str], user_instructions: str = "") -> str:
        """Write tasks to AGENT.md and record the iteration."""
        iteration = {
            "number": self.get_iteration_count() + 1,
            "started": datetime.now().isoformat(),
            "task_count": len(tasks),
            "tasks": tasks,
            "user_instructions": user_instructions,
            "status": "pending",
            "completed_tasks": [],
        }

        # Write AGENT.md
        path = write_agent_instructions(
            str(self.project_path),
            model_name="",
            tasks=tasks,
        )

        self._save_iteration(iteration)
        return path

    # ── Harvest learning after completion ────────
    def harvest_iteration(self, dm: DatasetManager) -> dict:
        """After agents finish, harvest their work as training data and update memory."""
        completed = get_completed_tasks(str(self.project_path))
        pending = get_pending_tasks(str(self.project_path))

        # Update iteration record
        history = self._load_iterations()
        if history:
            last = history[-1]
            last["status"] = "complete" if not pending else "partial"
            last["completed_tasks"] = completed
            last["finished"] = datetime.now().isoformat()
            self.iterations_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        # Harvest completed tasks as training examples
        ds_name = "iteration-learning"
        try:
            dm.create_dataset(ds_name, "Learned from iteration completions")
        except ValueError:
            pass

        count = 0
        for task in completed:
            dm.add_example(ds_name, TrainingExample(
                id=_uid(),
                prompt=f"Complete this coding task: {task}",
                completion=f"I completed the task: {task}. Changes were made to the project files using tools.",
                tags=["iteration", "completed-task"],
                source="iteration",
            ))
            count += 1

        # Update persistent agent memory
        if completed:
            memory_entry = f"Iteration {self.get_iteration_count()}:\n"
            memory_entry += f"- Completed {len(completed)}/{len(completed) + len(pending)} tasks\n"
            for t in completed[:10]:
                memory_entry += f"- Done: {t[:80]}\n"
            if pending:
                memory_entry += f"- Remaining: {len(pending)} tasks\n"
            self.append_agent_memory("Iteration Complete", memory_entry)

        return {
            "completed": len(completed),
            "pending": len(pending),
            "harvested": count,
            "iteration": self.get_iteration_count(),
        }
