"""
agent_core/planner.py
The main agent loop. Reads task, searches memory, plans, calls tools, summarizes.
"""

import json
import asyncio
from typing import AsyncGenerator, Optional, Callable
import logging

from models.ollama_client import OllamaClient
from agent_core.permissions import PermissionsEngine
from agent_core.memory_retriever import MemoryRetriever
from agent_core.session_manager import SessionManager
from agent_core.tool_router import ToolRouter

logger = logging.getLogger("planner")

SYSTEM_PROMPT = """You are OfflineAgent, a disciplined local coding assistant.

You operate in a layered permission system. Only call tools that are available to you.
Think step by step. Always read before writing. Always test after patching.

Your response format for tool calls must be valid JSON:
{"tool": "tool_name", "params": {"key": "value"}}

When you are done with a task, respond with:
{"done": true, "summary": "what was accomplished"}

If you need more information, respond with:
{"clarify": "your question"}

Otherwise for normal responses, respond in plain text.
"""


class Planner:
    """
    Main agent loop. One task at a time.
    Reads memory → plans → calls tools → summarizes → logs.
    """

    def __init__(
        self,
        permissions: PermissionsEngine,
        memory: MemoryRetriever,
        session: SessionManager,
        router: ToolRouter,
        on_event: Optional[Callable] = None,
    ):
        self.permissions = permissions
        self.memory = memory
        self.session = session
        self.router = router
        self.on_event = on_event  # WebSocket broadcast callback
        self.client = OllamaClient(profile="planner")
        self.running = False
        self.max_steps = 50

    async def emit(self, event_type: str, data: dict):
        """Broadcast an event to the UI."""
        if self.on_event:
            await self.on_event({"type": event_type, "data": data})

    async def run_task(self, task: str) -> AsyncGenerator[dict, None]:
        """
        Execute a full task loop. Yields events for the UI to consume.
        """
        self.running = True
        self.session.set_task(task)

        await self.emit("task_start", {"task": task})

        # Build context
        context = self.memory.get_relevant_context(task)
        recent = self.session.get_recent_conversation(turns=10)

        system = SYSTEM_PROMPT + f"\n\n{context}"
        system += f"\n\nAvailable tools: {', '.join(self.router.available_tools())}"
        system += f"\nCurrent permission mode: {self.permissions.mode} — {self.permissions.mode_name}"

        messages = recent + [{"role": "user", "content": task}]
        self.session.add_user_message(task)

        steps = 0
        while self.running and steps < self.max_steps:
            if self.permissions.kill_switch_active():
                await self.emit("kill_switch", {"msg": "Kill switch engaged. Agent halted."})
                break

            await self.emit("thinking", {"step": steps})

            try:
                # Stream tokens to the UI as they arrive. Big
                # perceptual speedup — first token typically lands
                # in 200-600ms instead of waiting 3-15s for the
                # full completion.
                stream = await self.client.chat(messages, system=system, stream=True)
                content_parts: list[str] = []
                first_token_emitted = False
                async for chunk in stream:
                    msg = chunk.get("message") or {}
                    delta = msg.get("content", "")
                    if delta:
                        if not first_token_emitted:
                            await self.emit("agent_first_token", {})
                            first_token_emitted = True
                        content_parts.append(delta)
                        await self.emit("agent_token", {"delta": delta})
                    if chunk.get("done"):
                        break
                content = "".join(content_parts).strip()
            except Exception as e:
                # The ollama client retries transient 500/502/503
                # internally. If we still landed here, it's a real
                # error worth surfacing to the user + session log.
                err = f"{type(e).__name__}: {e}"[:400]
                await self.emit("error", {
                    "msg": f"model error after retries: {err}",
                    "hint": "check that ollama is running and the planner model is pulled. try the same task again in 5-10s.",
                })
                self.session.add_agent_message(f"[error] model call failed: {err}")
                break

            self.session.add_agent_message(content)
            messages.append({"role": "assistant", "content": content})

            # Try to parse as action
            action = _try_parse_action(content)

            if action is None:
                # Plain text response — relay to user
                await self.emit("agent_message", {"content": content})
                break

            if "done" in action:
                summary = action.get("summary", "Task complete.")
                self.session.complete_task(summary)
                await self.emit("task_complete", {"summary": summary})
                break

            if "clarify" in action:
                await self.emit("clarify", {"question": action["clarify"]})
                break

            if "tool" in action:
                tool_name = action["tool"]
                params = action.get("params", {})

                await self.emit("tool_call", {"tool": tool_name, "params": params})

                result = await self.router.call(tool_name, params)

                await self.emit("tool_result", {
                    "tool": tool_name,
                    "success": result["success"],
                    "result": str(result.get("result", ""))[:1000],
                    "error": result.get("error"),
                })

                # Feed result back to model
                tool_msg = json.dumps(result)
                messages.append({"role": "user", "content": f"Tool result: {tool_msg}"})

            steps += 1

        self.running = False
        await self.emit("loop_end", {"steps": steps})

    def stop(self):
        self.running = False


def _try_parse_action(content: str) -> Optional[dict]:
    """Try to parse content as a JSON action. Returns None if it's plain text."""
    stripped = content.strip()
    if not stripped.startswith("{"):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Try to extract JSON from mixed content
        import re
        match = re.search(r'\{[^{}]+\}', stripped, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None
