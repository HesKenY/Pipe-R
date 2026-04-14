"""
agent_core/permissions.py
Layered permissions engine. Enforces mode-based access control on all tool calls.
"""

import os
import yaml
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("permissions")

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "permissions.yaml"
_KILL_SWITCH = Path(__file__).parent.parent / "config" / ".kill_switch"


def _load() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


class PermissionsEngine:
    """
    Enforces permission modes 0-3 on every tool call.
    Mode 0: Read only
    Mode 1: Workspace write
    Mode 2: Elevated dev
    Mode 3: Operator (desktop)
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
        logger.info(f"Permission mode changed: {self._mode} → {mode}")
        self._mode = mode

    def kill_switch_active(self) -> bool:
        """Returns True if the kill switch file exists."""
        return _KILL_SWITCH.exists()

    def arm_kill_switch(self) -> None:
        """Create kill switch file to halt agent."""
        _KILL_SWITCH.touch()
        logger.critical("KILL SWITCH ARMED")

    def disarm_kill_switch(self) -> None:
        """Remove kill switch file."""
        if _KILL_SWITCH.exists():
            _KILL_SWITCH.unlink()
        logger.info("Kill switch disarmed")

    def check(self, tool_name: str, path: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if a tool call is permitted in the current mode.
        Returns (allowed: bool, reason: str)
        """
        # Kill switch always wins
        if self.kill_switch_active():
            return False, "KILL SWITCH ACTIVE — agent halted"

        mode_cfg = self.config["modes"][self._mode]
        allow = mode_cfg.get("allow", {})

        # Check tool permission
        if not allow.get(tool_name, False):
            return False, f"Tool '{tool_name}' not permitted in Mode {self._mode} ({self.mode_name})"

        # Check path restrictions
        if path:
            normalized = str(Path(path).resolve()).lower()

            # Check blocked paths
            blocked = mode_cfg.get("blocked_paths", [])
            for bp in blocked:
                bp_expanded = os.path.expandvars(os.path.expanduser(bp)).lower()
                if normalized.startswith(bp_expanded):
                    return False, f"Path '{path}' is blocked in Mode {self._mode}"

            # Check restricted paths (must be within one of these)
            restricted = mode_cfg.get("restricted_paths", [])
            if restricted:
                root = Path(__file__).parent.parent.resolve()
                in_allowed = any(
                    normalized.startswith(str(root / rp).lower())
                    for rp in restricted
                )
                if not in_allowed:
                    return False, f"Path '{path}' is outside allowed workspace for Mode {self._mode}"

        return True, "OK"

    def check_command(self, cmd: str) -> tuple[bool, str]:
        """Check if a shell command is permitted."""
        if self.kill_switch_active():
            return False, "KILL SWITCH ACTIVE"

        mode_cfg = self.config["modes"][self._mode]
        allowed_cmds = mode_cfg.get("allowed_commands", [])

        if "*" in allowed_cmds:
            return True, "OK"

        cmd_base = cmd.strip().split()[0] if cmd.strip() else ""
        for ac in allowed_cmds:
            if cmd.strip().startswith(ac) or cmd_base == ac:
                return True, "OK"

        return False, f"Command not in allowlist for Mode {self._mode}: '{cmd_base}'"

    def requires_confirmation(self) -> bool:
        return self.config["modes"][self._mode].get("require_confirmation", False)

    def dry_run_default(self) -> bool:
        return self.safety.get("dry_run_default", True)

    def get_mode_info(self) -> dict:
        m = self.config["modes"][self._mode]
        return {
            "mode": self._mode,
            "name": m["name"],
            "description": m["description"],
            "color": m.get("color", "#fff"),
            "kill_switch": self.kill_switch_active(),
            "dry_run": self.dry_run_default(),
        }

    def all_modes(self) -> list[dict]:
        return [
            {
                "mode": k,
                "name": v["name"],
                "description": v["description"],
                "color": v.get("color", "#fff"),
            }
            for k, v in self.config["modes"].items()
        ]
