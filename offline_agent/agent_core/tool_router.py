"""
agent_core/tool_router.py
Dispatches tool calls from the model to the appropriate tool module.
Enforces permissions before every call. Logs all actions.
"""

import json
from typing import Any, Callable, Optional
import logging

from agent_core.permissions import PermissionsEngine
from agent_core.session_manager import SessionManager

logger = logging.getLogger("tool_router")


class ToolRouter:
    """
    Central dispatcher for all agent tool calls.
    Every tool is registered here. Permissions checked before every call.
    """

    def __init__(self, permissions: PermissionsEngine, session: SessionManager):
        self.permissions = permissions
        self.session = session
        self._registry: dict[str, Callable] = {}
        self._tool_meta: dict[str, dict] = {}

    def register(self, name: str, fn: Callable, min_mode: int = 0, description: str = ""):
        """Register a tool function."""
        self._registry[name] = fn
        self._tool_meta[name] = {"min_mode": min_mode, "description": description}

    async def call(self, tool_name: str, params: dict) -> dict:
        """
        Execute a tool call with full permission checks.
        Returns {"success": bool, "result": any, "error": str|None}
        """
        # Kill switch check
        if self.permissions.kill_switch_active():
            return {"success": False, "result": None, "error": "KILL SWITCH ACTIVE"}

        # Tool exists?
        if tool_name not in self._registry:
            return {"success": False, "result": None, "error": f"Unknown tool: {tool_name}"}

        # Mode check
        meta = self._tool_meta[tool_name]
        if self.permissions.mode < meta["min_mode"]:
            msg = (
                f"Tool '{tool_name}' requires Mode {meta['min_mode']} "
                f"— current mode is {self.permissions.mode} ({self.permissions.mode_name})"
            )
            self.session.log_tool_call(tool_name, params, msg, permitted=False)
            return {"success": False, "result": None, "error": msg}

        # Path-level permission check
        path = params.get("path") or params.get("cwd")
        perm_ok, perm_reason = self.permissions.check(tool_name, path)
        if not perm_ok:
            self.session.log_tool_call(tool_name, params, perm_reason, permitted=False)
            return {"success": False, "result": None, "error": perm_reason}

        # Command allowlist check
        if "cmd" in params:
            cmd_ok, cmd_reason = self.permissions.check_command(params["cmd"])
            if not cmd_ok:
                self.session.log_tool_call(tool_name, params, cmd_reason, permitted=False)
                return {"success": False, "result": None, "error": cmd_reason}

        # Execute
        try:
            fn = self._registry[tool_name]
            if _is_async(fn):
                result = await fn(**params)
            else:
                result = fn(**params)
            self.session.log_tool_call(tool_name, params, str(result), permitted=True)
            return {"success": True, "result": result, "error": None}
        except Exception as e:
            error_msg = f"Tool '{tool_name}' raised: {type(e).__name__}: {e}"
            logger.exception(error_msg)
            self.session.log_tool_call(tool_name, params, error_msg, permitted=True)
            return {"success": False, "result": None, "error": error_msg}

    def get_tool_definitions(self) -> list[dict]:
        """Return Ollama-compatible tool definitions for the current permission mode."""
        definitions = []
        for name, meta in self._tool_meta.items():
            if self.permissions.mode >= meta["min_mode"]:
                definitions.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": meta["description"],
                    }
                })
        return definitions

    def available_tools(self) -> list[str]:
        return [
            name for name, meta in self._tool_meta.items()
            if self.permissions.mode >= meta["min_mode"]
        ]


def _is_async(fn) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(fn)
