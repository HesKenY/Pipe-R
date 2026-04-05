"""ProjectWorker — analyze any folder, plan tasks, execute, auto-iterate."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from collections import Counter


class ProjectWorker:
    """Manages the full work cycle on any project folder."""

    def __init__(self, project_path: str, max_iterations: int = 3, stop_on_error: bool = False):
        self.root = Path(project_path).resolve()
        self.max_iterations = max_iterations
        self.stop_on_error = stop_on_error
        self.forge_dir = self.root / ".forgeagent"
        self.claude_dir = self.root / ".claude"

    def analyze(self) -> dict:
        """Deep scan project and return structured analysis."""
        skip = {".git", "node_modules", "__pycache__", ".next", "dist",
                "build", "venv", ".venv", ".forgeagent", ".memory", ".claude"}

        files_by_ext: Counter = Counter()
        total_lines = 0
        entry_points: list[str] = []
        config_files: list[str] = []
        test_files: list[str] = []
        todos: list[str] = []
        all_files: list[str] = []
        functions: list[str] = []

        for fp in self.root.rglob("*"):
            if fp.is_dir() or any(s in fp.parts for s in skip):
                continue
            rel = str(fp.relative_to(self.root)).replace("\\", "/")
            ext = fp.suffix.lower()
            all_files.append(rel)
            files_by_ext[ext] += 1

            name = fp.name.lower()
            if name in ("main.py", "app.py", "index.ts", "index.js", "server.ts",
                         "server.js", "main.go", "main.rs", "page.tsx", "__main__.py"):
                entry_points.append(rel)
            if name in ("package.json", "pyproject.toml", "cargo.toml", "go.mod",
                         "tsconfig.json", "requirements.txt", "dockerfile",
                         "docker-compose.yml", ".env.example"):
                config_files.append(rel)
            if "test" in name or name.startswith("test_") or ".test." in name or ".spec." in name:
                test_files.append(rel)

            if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go"):
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")
                    total_lines += len(lines)
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if "TODO" in stripped or "FIXME" in stripped or "HACK" in stripped:
                            todos.append(f"{rel}:{i+1}: {stripped[:80]}")
                        if stripped.startswith("def ") or stripped.startswith("async def "):
                            func_name = stripped.split("(")[0].replace("def ", "").replace("async ", "").strip()
                            functions.append(f"{rel}:{func_name}")
                        elif stripped.startswith("export function ") or stripped.startswith("export async function "):
                            func_name = stripped.split("(")[0].split("function ")[-1].strip()
                            functions.append(f"{rel}:{func_name}")
                except Exception:
                    pass

        framework = self._detect_framework()

        return {
            "path": str(self.root),
            "name": self.root.name,
            "framework": framework,
            "total_files": len(all_files),
            "total_lines": total_lines,
            "files_by_ext": dict(files_by_ext.most_common(10)),
            "entry_points": entry_points[:10],
            "config_files": config_files,
            "test_files": test_files[:20],
            "has_tests": len(test_files) > 0,
            "todos": todos[:20],
            "functions": functions[:50],
            "dirs": sorted(set(str(Path(f).parent) for f in all_files if "/" in f))[:15],
        }

    def _detect_framework(self) -> str:
        if (self.root / "package.json").exists():
            try:
                pkg = json.loads((self.root / "package.json").read_text())
                deps = set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys())
                if "next" in deps: return "nextjs"
                if "react" in deps: return "react"
                if "express" in deps: return "express"
                if "vue" in deps: return "vue"
                return "node"
            except Exception:
                return "node"
        if (self.root / "pyproject.toml").exists() or (self.root / "requirements.txt").exists():
            return "python"
        if (self.root / "Cargo.toml").exists(): return "rust"
        if (self.root / "go.mod").exists(): return "go"
        return "unknown"

    def plan(self, analysis: dict | None = None, user_instructions: str = "") -> list[str]:
        """Generate task list based on analysis."""
        if not analysis:
            analysis = self.analyze()
        tasks = []

        if user_instructions:
            for line in user_instructions.strip().split("\n"):
                line = line.strip().lstrip("-*0123456789.").strip()
                if line and len(line) > 5:
                    tasks.append(line)

        if not analysis["has_tests"]:
            tasks.append("Create tests for the core modules.")
        if analysis["todos"]:
            tasks.append(f"Resolve {len(analysis['todos'])} TODO/FIXME comments.")

        fw = analysis["framework"]
        if fw == "nextjs":
            tasks.extend([
                "Add error handling to all API routes.",
                "Add SEO metadata to all pages.",
                "Add loading skeletons for data-fetching pages.",
            ])
        elif fw == "python":
            tasks.extend([
                "Add type hints to all public functions.",
                "Add error handling to file I/O and network ops.",
            ])

        tasks.extend([
            "Review code for security issues.",
            "Find hardcoded values and move to config.",
        ])
        return tasks[:20]

    def save_analysis(self, analysis: dict) -> str:
        """Save to .claude/analysis.md."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Analysis — {analysis['name']}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Framework: {analysis['framework']} | {analysis['total_files']} files | {analysis['total_lines']} lines",
            "",
        ]
        for ext, count in analysis["files_by_ext"].items():
            lines.append(f"- {ext}: {count}")
        if analysis["entry_points"]:
            lines.append("\n## Entry Points")
            for ep in analysis["entry_points"]:
                lines.append(f"- {ep}")
        if analysis["todos"]:
            lines.append(f"\n## TODOs ({len(analysis['todos'])})")
            for t in analysis["todos"][:10]:
                lines.append(f"- {t}")

        content = "\n".join(lines)
        path = self.claude_dir / "analysis.md"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def execute(self, tasks: list[str]) -> None:
        """Write tasks to AGENT.md for agents to execute."""
        from ..deploy.agent_instructions import write_agent_instructions
        write_agent_instructions(str(self.root), tasks=tasks)

    def iterate(self) -> dict:
        """Full cycle: analyze -> plan -> write tasks -> harvest."""
        analysis = self.analyze()
        self.save_analysis(analysis)
        tasks = self.plan(analysis)
        self.execute(tasks)
        return {"analysis": analysis, "tasks": tasks}
