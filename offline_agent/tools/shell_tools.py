"""
tools/shell_tools.py
Safe subprocess execution. Timeout enforced. Output capped. 
Command allowlist enforced upstream by ToolRouter/PermissionsEngine.
"""

import subprocess
from tools.win_subprocess import run as _win_run
import sys
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("shell_tools")

DEFAULT_TIMEOUT = 120
MAX_OUTPUT_CHARS = 8000


def run_command(cmd: str, cwd: str = ".", timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Execute a shell command and return stdout + stderr.
    Output capped at MAX_OUTPUT_CHARS to protect context window.
    """
    cwd_path = Path(cwd).resolve()
    if not cwd_path.exists():
        return f"ERROR: Working directory not found: {cwd}"

    logger.info(f"run_command: {cmd!r} in {cwd_path}")

    try:
        result = _win_run(
            cmd,
            shell=True,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        combined = out + (f"\n[stderr]\n{err}" if err.strip() else "")
        if len(combined) > MAX_OUTPUT_CHARS:
            combined = combined[:MAX_OUTPUT_CHARS] + f"\n...[truncated at {MAX_OUTPUT_CHARS} chars]"
        rc = result.returncode
        header = f"[rc={rc}] $ {cmd}\n"
        return header + combined
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout}s: {cmd}"
    except Exception as e:
        return f"ERROR running command: {e}"


def run_tests(target: str = "", cwd: str = ".") -> str:
    """Run the test suite. Detects pytest or npm test."""
    cwd_path = Path(cwd).resolve()

    # Auto-detect test runner
    if (cwd_path / "package.json").exists() and not target:
        cmd = "npm test -- --watchAll=false"
    elif shutil.which("pytest"):
        cmd = f"pytest {target} -v --tb=short" if target else "pytest -v --tb=short"
    else:
        cmd = f"python -m pytest {target} -v --tb=short"

    return run_command(cmd, cwd=str(cwd_path), timeout=180)


def run_formatter(path: str, formatter: str = "auto") -> str:
    """Run code formatter on a file or directory."""
    p = Path(path)

    if formatter == "auto":
        if p.suffix == ".py" or p.is_dir():
            formatter = "black"
        elif p.suffix in {".js", ".ts", ".jsx", ".tsx", ".json"}:
            formatter = "prettier"
        else:
            return f"Cannot auto-detect formatter for: {path}"

    if formatter == "black":
        if not shutil.which("black"):
            return "ERROR: black not installed. Run: pip install black"
        return run_command(f"black {path}", cwd=str(p.parent if p.is_file() else p))
    elif formatter == "prettier":
        if not shutil.which("prettier"):
            return "ERROR: prettier not installed. Run: npm install -g prettier"
        return run_command(f"prettier --write {path}", cwd=str(p.parent if p.is_file() else p))

    return f"Unknown formatter: {formatter}"


def run_linter(path: str, linter: str = "auto") -> str:
    """Run linter on a file or directory."""
    p = Path(path)

    if linter == "auto":
        if p.suffix == ".py" or p.is_dir():
            linter = "flake8"
        elif p.suffix in {".js", ".ts"}:
            linter = "eslint"
        else:
            return f"Cannot auto-detect linter for: {path}"

    if linter == "flake8":
        if not shutil.which("flake8"):
            return "ERROR: flake8 not installed. Run: pip install flake8"
        return run_command(f"flake8 {path} --max-line-length=120")
    elif linter == "eslint":
        return run_command(f"npx eslint {path}")

    return f"Unknown linter: {linter}"


def install_package(package: str, manager: str = "pip") -> str:
    """Install a package. Requires Mode 2+."""
    if manager == "pip":
        return run_command(
            f"{sys.executable} -m pip install {package}",
            timeout=300
        )
    elif manager == "npm":
        return run_command(f"npm install {package}", timeout=300)
    elif manager == "yarn":
        return run_command(f"yarn add {package}", timeout=300)
    return f"Unknown package manager: {manager}"


def which(name: str) -> str:
    """Check if a command is available on PATH."""
    found = shutil.which(name)
    return found if found else f"{name}: not found on PATH"
