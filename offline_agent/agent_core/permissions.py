"""
agent_core/permissions.py
Layered permissions engine for the offline developer agent.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger("permissions")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "permissions.yaml"
KILL_SWITCH = Path(__file__).parent.parent / "config" / ".kill_switch"
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

WRITE_TOOLS = {
    "write_file",
    "apply_patch",
    "apply_multi_patch",
    "propose_patch",
    "approve_patch",
    "reject_patch",
    "revert_last_patch",
    "delete_file",
    "write_brain_file",
    "append_session_entry",
    "open_task",
    "close_task",
    "git_add",
    "git_commit",
    "git_branch",
    "git_stash",
}


def _load() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_config_path(raw_path: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


class PermissionsEngine:
    """
    Enforces permission modes 0-3 on every tool call.
    Mode 0: Read only
    Mode 1: Workspace write
    Mode 2: Elevated dev
    Mode 3: Operator
    """

    def __init__(self, initial_mode: int = 0):
        self.config = _load()
        self._mode = initial_mode
        self.safety = self.config.get("safety", {})

    @property
    def mode(self) -> int:
        return self._mode

    @property
    def mode_name(self) -> str:
        return self.config["modes"][self._mode]["name"]

    @property
    def mode_color(self) -> str:
        return self.config["modes"][self._mode].get("color", "#ffffff")

    def set_mode(self, mode: int) -> None:
        if mode not in self.config["modes"]:
            raise ValueError(f"Invalid mode: {mode}")
        logger.info("Permission mode changed: %s -> %s", self._mode, mode)
        self._mode = mode

    def kill_switch_active(self) -> bool:
        return KILL_SWITCH.exists()

    def arm_kill_switch(self) -> None:
        KILL_SWITCH.touch()
        logger.critical("KILL SWITCH ARMED")

    def disarm_kill_switch(self) -> None:
        if KILL_SWITCH.exists():
            KILL_SWITCH.unlink()
        logger.info("Kill switch disarmed")

    def check(self, tool_name: str, path: Optional[str] = None) -> tuple[bool, str]:
        """
        Check whether a tool call is permitted in the current mode.
        Returns (allowed, reason).
        """
        if self.kill_switch_active():
            return False, "KILL SWITCH ACTIVE - agent halted"

        mode_cfg = self.config["modes"][self._mode]
        allow = mode_cfg.get("allow", {})
        if not allow.get(tool_name, False):
            return False, f"Tool '{tool_name}' not permitted in Mode {self._mode} ({self.mode_name})"

        if not path:
            return True, "OK"

        normalized = str(Path(path).resolve()).lower()
        basename = Path(path).name.lower()

        if tool_name in WRITE_TOOLS:
            for blocked_path in self.safety.get("always_blocked_write_paths", []):
                blocked_lower = blocked_path.lower()
                if blocked_lower.startswith("*."):
                    if basename.endswith(blocked_lower[1:]):
                        return False, f"Write to '{path}' blocked by safety rules (matches {blocked_path})"
                    continue

                resolved_blocked = str(_resolve_config_path(blocked_path)).lower()
                if normalized.startswith(resolved_blocked):
                    return False, f"Write to '{path}' blocked by safety rules"

        for blocked_path in mode_cfg.get("blocked_paths", []):
            resolved_blocked = str(_resolve_config_path(blocked_path)).lower()
            if normalized.startswith(resolved_blocked):
                return False, f"Path '{path}' is blocked in Mode {self._mode}"

        restricted = mode_cfg.get("restricted_paths", [])
        if restricted:
            allowed_roots = [str(_resolve_config_path(item)).lower() for item in restricted]
            in_allowed = any(normalized.startswith(root) for root in allowed_roots)
            if not in_allowed:
                return False, f"Path '{path}' is outside the allowed workspace for Mode {self._mode}"

        return True, "OK"

    def check_command(self, cmd: str) -> tuple[bool, str]:
        if self.kill_switch_active():
            return False, "KILL SWITCH ACTIVE"

        cmd_stripped = cmd.strip()
        cmd_lower = cmd_stripped.lower()

        for blocked_cmd in self.safety.get("blocked_commands", []):
            if blocked_cmd.lower() in cmd_lower:
                logger.warning(
                    "BLOCKED command (safety): '%s' matched '%s'",
                    cmd_stripped[:80],
                    blocked_cmd,
                )
                return False, f"Command blocked by safety rules: contains '{blocked_cmd}'"

        mode_cfg = self.config["modes"][self._mode]
        allowed_cmds = mode_cfg.get("allowed_commands", [])
        if "*" in allowed_cmds:
            return True, "OK"

        cmd_base = cmd_stripped.split()[0] if cmd_stripped else ""
        for allowed in allowed_cmds:
            if cmd_stripped.startswith(allowed) or cmd_base == allowed:
                return True, "OK"

        return False, f"Command not in allowlist for Mode {self._mode}: '{cmd_base}'"

    def requires_confirmation(self) -> bool:
        return self.config["modes"][self._mode].get("require_confirmation", False)

    def dry_run_default(self) -> bool:
        return self.safety.get("dry_run_default", True)

    def get_mode_info(self) -> dict:
        mode_cfg = self.config["modes"][self._mode]
        return {
            "mode": self._mode,
            "name": mode_cfg["name"],
            "description": mode_cfg["description"],
            "color": mode_cfg.get("color", "#fff"),
            "kill_switch": self.kill_switch_active(),
            "dry_run": self.dry_run_default(),
        }

    def all_modes(self) -> list[dict]:
        return [
            {
                "mode": mode_num,
                "name": cfg["name"],
                "description": cfg["description"],
                "color": cfg.get("color", "#fff"),
            }
            for mode_num, cfg in self.config["modes"].items()
        ]
