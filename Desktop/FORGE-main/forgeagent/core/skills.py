"""SkillTracker — builds model skill profiles from task history."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


CATEGORIES = ["code-gen", "debugging", "testing", "refactoring", "docs", "devops", "tool-use"]

# Keywords that map tasks to categories
CATEGORY_KEYWORDS = {
    "code-gen": ["create", "write", "build", "implement", "add", "generate"],
    "debugging": ["fix", "bug", "error", "debug", "crash", "broken"],
    "testing": ["test", "pytest", "vitest", "spec", "assert", "coverage"],
    "refactoring": ["refactor", "clean", "simplify", "extract", "rename", "reorganize"],
    "docs": ["readme", "doc", "comment", "docstring", "changelog"],
    "devops": ["docker", "deploy", "ci", "cd", "pipeline", "config", "env"],
    "tool-use": ["read_file", "write_file", "edit_file", "bash", "search", "glob"],
}


class SkillTracker:
    """Tracks model performance per category across tasks."""

    def __init__(self, memory_dir: str):
        self.history_file = Path(memory_dir) / "task_history.json"
        Path(memory_dir).mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save(self, history: list[dict]):
        # Keep last 500
        if len(history) > 500:
            history = history[-500:]
        self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def record_task(self, model: str, task: str, success: bool,
                    tools_used: list[str] | None = None, project: str = ""):
        """Record a completed task."""
        category = self._categorize(task)
        entry = {
            "model": model,
            "task": task[:200],
            "category": category,
            "success": success,
            "tools": tools_used or [],
            "project": project,
            "timestamp": datetime.now().isoformat(),
        }
        history = self._load()
        history.append(entry)
        self._save(history)

    def rate_model(self, model: str, category: str = "") -> int:
        """Rate a model 0-100 in a category (or overall)."""
        history = self._load()
        relevant = [h for h in history if h["model"] == model]
        if category:
            relevant = [h for h in relevant if h["category"] == category]
        if not relevant:
            return 0
        successes = sum(1 for h in relevant if h["success"])
        return round(successes / len(relevant) * 100)

    def best_model_for(self, task: str) -> str | None:
        """Return the model name best suited for a task."""
        category = self._categorize(task)
        history = self._load()
        models = set(h["model"] for h in history)
        if not models:
            return None
        scores = {}
        for model in models:
            scores[model] = self.rate_model(model, category)
        return max(scores, key=scores.get) if scores else None

    def get_profile(self, model: str) -> dict:
        """Get full skill profile for a model."""
        profile = {}
        for cat in CATEGORIES:
            profile[cat] = self.rate_model(model, cat)
        profile["overall"] = self.rate_model(model)
        profile["total_tasks"] = len([h for h in self._load() if h["model"] == model])
        return profile

    def get_all_profiles(self) -> dict[str, dict]:
        """Get profiles for all known models."""
        history = self._load()
        models = set(h["model"] for h in history)
        return {m: self.get_profile(m) for m in models}

    def _categorize(self, task: str) -> str:
        """Map a task description to a category."""
        task_lower = task.lower()
        scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in task_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "code-gen"
