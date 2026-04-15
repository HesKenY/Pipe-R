"""
models/ollama_client.py
Wrapper around the Ollama local API.
Handles chat, tool calling, structured outputs, and model management.
"""

import json
import re
import httpx
import asyncio
from typing import Any, AsyncGenerator, Optional
from pathlib import Path
import yaml

# ANSI CSI + OSC sequences that ollama run and some models
# leak into responses. Strip before passing text upward so
# chat-log + memory don't get polluted.
_ANSI_CSI = re.compile(r"\u001b\[\??[0-9;]*[a-zA-Z]")
_ANSI_OSC = re.compile(r"\u001b\][^\u0007]*\u0007")


def strip_ansi(s: str) -> str:
    if not s:
        return ""
    return _ANSI_OSC.sub("", _ANSI_CSI.sub("", s))


def strip_json_fence(s: str) -> str:
    """Remove a ```json ... ``` wrapper if present."""
    if not s:
        return ""
    t = s.strip()
    if t.startswith("```"):
        # drop opening fence (with optional language tag)
        t = re.sub(r"^```[a-zA-Z0-9]*\n?", "", t)
        # drop closing fence
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config" / "models.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


CONFIG = _load_config()
BASE_URL = CONFIG["ollama"]["base_url"]
TIMEOUT = CONFIG["ollama"]["timeout"]


class OllamaClient:
    """Async client for the Ollama local API."""

    def __init__(self, profile: str = "planner"):
        self.profile = CONFIG["models"]["profiles"].get(
            profile, CONFIG["models"]["profiles"]["planner"]
        )
        self.model = self.profile["model"]
        self.base_url = BASE_URL

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> dict | AsyncGenerator:
        """Send a chat request to Ollama."""
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "num_ctx": self.profile.get("num_ctx", 32768),
                "temperature": self.profile.get("temperature", 0.2),
                "top_p": self.profile.get("top_p", 0.9),
            },
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        if stream:
            return self._stream_chat(payload)
        else:
            return await self._chat_once(payload)

    async def _chat_once(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Strip ANSI from the assistant content before
            # returning — downstream memory + logs will reuse
            # this string and we don't want terminal noise in
            # the brain index.
            msg = data.get("message", {})
            if isinstance(msg, dict) and "content" in msg:
                msg["content"] = strip_ansi(msg["content"])
                data["message"] = msg
            return data

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: Optional[str] = None,
    ) -> dict:
        """Force model to output valid JSON matching schema."""
        sys_prompt = (
            (system + "\n\n") if system else ""
        ) + (
            f"You MUST respond with ONLY valid JSON matching this schema. "
            f"No explanation, no markdown, no backticks.\nSchema: {json.dumps(schema)}"
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat(messages, system=sys_prompt)
        raw = strip_ansi(result.get("message", {}).get("content", ""))
        raw = strip_json_fence(raw)
        # Last-ditch: grab the first {...} block if there's still noise
        if not raw.startswith("{"):
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                raw = m.group(0)
        return json.loads(raw)

    async def list_models(self) -> list[str]:
        """Return list of locally available Ollama models."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def health_check(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def pull_model(self, model_name: str) -> AsyncGenerator[str, None]:
        """Pull a model from Ollama registry (streaming progress)."""
        payload = {"name": model_name, "stream": True}
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("POST", f"{self.base_url}/api/pull", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)
