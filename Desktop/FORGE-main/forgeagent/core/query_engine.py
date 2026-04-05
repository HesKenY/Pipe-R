"""Multi-round query engine with tool orchestration and streaming."""
from __future__ import annotations
from datetime import datetime, timezone
from ..utils.helpers import make_id
from ..config import AppConfig
from .interfaces import ChatMessage, ToolCall, ModelTurnResult, ToolContext, ToolRegistry
from ..providers.ollama.client import OllamaClient
from ..providers.ollama.tool_protocol import build_tool_instructions, parse_tool_calls
from ..memory.session_store import SessionStore


class QueryEngine:
    def __init__(self, config: AppConfig, tools: ToolRegistry):
        self.config = config
        self.tools = tools
        self.client = OllamaClient(config.ollama_base_url)
        self.store = SessionStore(config.sessions_dir)
        self.messages: list[ChatMessage] = []
        self.messages.append(ChatMessage(
            id=make_id(), role="system",
            content=self._build_system_prompt(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    # ── Accessors ──────────────────────────────────
    def get_messages(self) -> list[ChatMessage]:
        return list(self.messages)

    def get_model(self) -> str:
        return self.config.model

    def set_model(self, model: str) -> None:
        self.config.model = model

    def clear_messages(self) -> None:
        self.messages = [ChatMessage(
            id=make_id(), role="system",
            content=self._build_system_prompt(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )]

    async def save_session(self) -> str:
        return await self.store.save(self.messages)

    def restore_messages(self, messages: list[ChatMessage]) -> None:
        self.messages = messages

    # ── Multi-round query ──────────────────────────
    async def submit_user_message(
        self,
        content: str,
        on_stream: object = None,
        on_tool: object = None,
    ) -> ModelTurnResult:
        now = datetime.now(timezone.utc).isoformat()
        self.messages.append(ChatMessage(id=make_id(), role="user", content=content, timestamp=now))

        round_num = 0
        all_tool_calls: list[ToolCall] = []

        while round_num < self.config.max_tool_rounds:
            round_num += 1

            # Stream response
            full_response = ""
            try:
                async for chunk in self.client.chat_stream(
                    model=self.config.model,
                    messages=self.messages,
                    temperature=self.config.temperature,
                ):
                    full_response += chunk
                    if on_stream and "```tool" not in full_response:
                        on_stream(chunk)  # type: ignore
            except Exception:
                full_response = await self.client.chat(
                    model=self.config.model,
                    messages=self.messages,
                    temperature=self.config.temperature,
                )

            # Parse tool calls
            assistant_text, tool_calls = parse_tool_calls(full_response)

            if not tool_calls:
                text = assistant_text or full_response
                msg = ChatMessage(id=make_id(), role="assistant", content=text, timestamp=now)
                self.messages.append(msg)
                await self.store.overwrite_latest(self.messages)
                return ModelTurnResult(assistant_message=msg, tool_calls=all_tool_calls, tool_rounds=round_num)

            # Execute tools
            limited = tool_calls[:self.config.max_tool_calls_per_turn]
            self.messages.append(ChatMessage(id=make_id(), role="assistant", content=full_response, timestamp=now))

            for call in limited:
                tool = self.tools.get(call.tool_name)
                if on_tool:
                    on_tool(call.tool_name, call.input)  # type: ignore

                if tool:
                    try:
                        result = await tool.run(call.input, ToolContext(cwd=self.config.cwd, memory_dir=self.config.memory_dir))
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = f"Tool not found: {call.tool_name}"

                self.messages.append(ChatMessage(
                    id=make_id(), role="tool", name=call.tool_name,
                    content=result[:8000], timestamp=now,
                ))
                all_tool_calls.append(call)

        # Max rounds
        fallback = ChatMessage(id=make_id(), role="assistant", content="(max tool rounds reached)", timestamp=now)
        self.messages.append(fallback)
        return ModelTurnResult(assistant_message=fallback, tool_calls=all_tool_calls, tool_rounds=round_num)

    # ── Summarize ──────────────────────────────────
    async def summarize(self, prompt: str) -> str:
        return await self.client.chat(
            model=self.config.model,
            messages=[ChatMessage(id=make_id(), role="user", content=prompt, timestamp=datetime.now(timezone.utc).isoformat())],
            temperature=0.3,
        )

    # ── Compact ────────────────────────────────────
    async def compact(self) -> str:
        user_assistant = [m for m in self.messages if m.role in ("user", "assistant")]
        if len(user_assistant) < 4:
            return "Not enough history to compact."

        transcript = "\n".join(f"[{m.role}] {m.content[:300]}" for m in user_assistant)
        summary = await self.summarize(
            "Summarize this conversation into a compact technical context for continued work. "
            "Preserve: decisions made, files modified, current task state, key facts. "
            "Format as structured bullet points.\n\n" + transcript
        )

        old_count = len(self.messages)
        now = datetime.now(timezone.utc).isoformat()
        self.messages = [
            ChatMessage(id=make_id(), role="system", content=self._build_system_prompt(), timestamp=now),
            ChatMessage(id=make_id(), role="user", content=f"[Compacted context from {old_count} messages]\n{summary}", timestamp=now),
            ChatMessage(id=make_id(), role="assistant", content="Context restored. Ready to continue.", timestamp=now),
        ]
        return f"Compacted {old_count} messages -> 3. Context preserved."

    # ── System prompt ──────────────────────────────
    def _build_system_prompt(self) -> str:
        return self.config.system_prompt + "\n\n" + build_tool_instructions(list(self.tools.values()))
