"""Project profile system — persistent config for deployed agents."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class ProjectProfile:
    """Manages .forgeagent/profile.json for a project folder."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.agent_dir = self.project_path / ".forgeagent"
        self.profile_file = self.agent_dir / "profile.json"
        self.log_file = self.agent_dir / "agent.log"

    @property
    def exists(self) -> bool:
        return self.profile_file.exists()

    def create(self, name: str, model: str, template: str = "fullstack",
               git_remote: str = "", auto_commit: bool = False,
               auto_push: bool = False, branch: str = "main") -> dict:
        """Create or update project profile."""
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("memory", "sessions", "dreams", "logs"):
            (self.agent_dir / sub).mkdir(exist_ok=True)

        profile = {
            "name": name,
            "model": model,
            "template": template,
            "projectPath": str(self.project_path),
            "created": datetime.now().isoformat(),
            "status": "stopped",
            # Git settings
            "git": {
                "remote": git_remote,
                "branch": branch,
                "autoCommit": auto_commit,
                "autoPush": auto_push,
            },
            # Agent behavior
            "settings": {
                "maxToolRounds": 8,
                "maxToolCallsPerTurn": 4,
                "temperature": 0.7,
                "dreamInterval": 10,
                "logToChat": True,
            },
        }
        self._save(profile)
        return profile

    def load(self) -> dict | None:
        if not self.profile_file.exists():
            return None
        try:
            return json.loads(self.profile_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def update(self, updates: dict) -> dict:
        profile = self.load() or {}
        profile.update(updates)
        self._save(profile)
        return profile

    def update_git(self, **kwargs) -> dict:
        profile = self.load() or {}
        git = profile.get("git", {})
        git.update(kwargs)
        profile["git"] = git
        self._save(profile)
        return profile

    def update_settings(self, **kwargs) -> dict:
        profile = self.load() or {}
        settings = profile.get("settings", {})
        settings.update(kwargs)
        profile["settings"] = settings
        self._save(profile)
        return profile

    def set_status(self, status: str) -> None:
        profile = self.load() or {}
        profile["status"] = status
        profile["lastStatusChange"] = datetime.now().isoformat()
        self._save(profile)

    def append_log(self, message: str, level: str = "info") -> None:
        """Append to agent.log."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level.upper()}] {message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def read_log(self, lines: int = 50) -> str:
        """Read last N lines of agent.log."""
        if not self.log_file.exists():
            return ""
        all_lines = self.log_file.read_text(encoding="utf-8").strip().split("\n")
        return "\n".join(all_lines[-lines:])

    def clear_log(self) -> None:
        if self.log_file.exists():
            self.log_file.write_text("", encoding="utf-8")

    # ── Git operations ────────────────────────────
    def git_status(self) -> str:
        try:
            r = subprocess.run(["git", "status", "--short"],
                               capture_output=True, text=True, timeout=10,
                               cwd=str(self.project_path))
            return r.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    def git_commit(self, message: str) -> dict:
        try:
            subprocess.run(["git", "add", "-A"],
                           capture_output=True, text=True, timeout=30,
                           cwd=str(self.project_path), check=True)
            r = subprocess.run(["git", "commit", "-m", message],
                               capture_output=True, text=True, timeout=30,
                               cwd=str(self.project_path))
            if r.returncode == 0:
                self.append_log(f"git commit: {message}")
                return {"success": True, "message": r.stdout.strip()}
            return {"success": False, "message": r.stderr.strip() or r.stdout.strip()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def git_push(self) -> dict:
        profile = self.load() or {}
        git = profile.get("git", {})
        remote = git.get("remote", "origin")
        branch = git.get("branch", "main")
        try:
            r = subprocess.run(["git", "push", remote, branch],
                               capture_output=True, text=True, timeout=60,
                               cwd=str(self.project_path))
            if r.returncode == 0:
                self.append_log(f"git push {remote} {branch}")
                return {"success": True, "message": r.stdout.strip() or "Pushed"}
            return {"success": False, "message": r.stderr.strip()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def git_log(self, n: int = 10) -> str:
        try:
            r = subprocess.run(["git", "log", f"--oneline", f"-{n}"],
                               capture_output=True, text=True, timeout=10,
                               cwd=str(self.project_path))
            return r.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    def _save(self, profile: dict) -> None:
        self.profile_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")
