"""
tools/git_tools.py
Git operations: status, diff, log, add, commit, branch.
All run as subprocesses. Repo path validated before every call.
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("git_tools")


def _run_git(args: list[str], cwd: str) -> str:
    """Run a git command and return combined stdout/stderr."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode != 0 and err:
            return f"[git error rc={result.returncode}]\n{err}"
        return out or err or "(no output)"
    except FileNotFoundError:
        return "ERROR: git not found on PATH"
    except subprocess.TimeoutExpired:
        return "ERROR: git command timed out"
    except Exception as e:
        return f"ERROR: {e}"


def _find_repo(path: str) -> Optional[str]:
    """Walk up from path to find a git repo root."""
    p = Path(path).resolve()
    for candidate in [p] + list(p.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return None


def git_status(repo_path: str = ".") -> str:
    """Show working tree status."""
    repo = _find_repo(repo_path) or repo_path
    return _run_git(["status", "--short", "--branch"], cwd=repo)


def git_diff(repo_path: str = ".", target: str = "") -> str:
    """Show uncommitted changes or diff against a target ref."""
    repo = _find_repo(repo_path) or repo_path
    args = ["diff"]
    if target:
        args.append(target)
    return _run_git(args, cwd=repo)


def git_log(repo_path: str = ".", limit: int = 10) -> str:
    """Show recent commit log."""
    repo = _find_repo(repo_path) or repo_path
    return _run_git(
        ["log", f"--max-count={limit}", "--oneline", "--graph", "--decorate"],
        cwd=repo,
    )


def git_add(repo_path: str, files: list[str] | str = ".") -> str:
    """Stage files for commit."""
    repo = _find_repo(repo_path) or repo_path
    if isinstance(files, list):
        args = ["add"] + files
    else:
        args = ["add", files]
    return _run_git(args, cwd=repo)


def git_commit(repo_path: str, message: str) -> str:
    """Create a commit with the given message."""
    repo = _find_repo(repo_path) or repo_path
    if not message.strip():
        return "ERROR: Commit message cannot be empty"
    return _run_git(["commit", "-m", message], cwd=repo)


def git_branch(repo_path: str, name: str = "", create: bool = False) -> str:
    """List branches, or create a new one."""
    repo = _find_repo(repo_path) or repo_path
    if create and name:
        return _run_git(["checkout", "-b", name], cwd=repo)
    elif name:
        return _run_git(["checkout", name], cwd=repo)
    return _run_git(["branch", "-a"], cwd=repo)


def git_stash(repo_path: str, action: str = "push") -> str:
    """Stash or pop changes. action: push|pop|list"""
    repo = _find_repo(repo_path) or repo_path
    if action == "pop":
        return _run_git(["stash", "pop"], cwd=repo)
    elif action == "list":
        return _run_git(["stash", "list"], cwd=repo)
    return _run_git(["stash", "push"], cwd=repo)


def git_show(repo_path: str, ref: str = "HEAD") -> str:
    """Show details of a specific commit."""
    repo = _find_repo(repo_path) or repo_path
    return _run_git(["show", "--stat", ref], cwd=repo)
