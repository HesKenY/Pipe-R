"""
models/ollama_client.py
Wrapper around the local Ollama API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
import yaml

logger = logging.getLogger("ollama_client")

ANSI_CSI = re.compile(r"\u001b\[\??[0-9;]*[a-zA-Z]")
ANSI_OSC = re.compile(r"\u001b\][^\u0007]*\u0007")


def strip_ansi(s: str) -> str:
    if not s:
        return ""
    return ANSI_OSC.sub("", ANSI_CSI.sub("", s))


def strip_json_fence(s: str) -> str:
    if not s:
        return ""
    text = s.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config" / "models.yaml"
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = _load_config()
BASE_URL = CONFIG["ollama"]["base_url"]
TIMEOUT = CONFIG["ollama"]["timeout"]


class OllamaClient:
    """Async client for the local Ollama API."""

    def __init__(self, profile: str = "planner"):
        self.profile_name = profile
        self.config = CONFIG
        self.profile = CONFIG["models"]["profiles"].get(
            profile, CONFIG["models"]["profiles"]["planner"]
        )
        self.preferred_model = self.profile["model"]
        self.model = self.preferred_model
        self.base_url = BASE_URL
        self._resolved = False
        self._resolution = {
            "profile": self.profile_name,
            "preferred_model": self.preferred_model,
            "active_model": self.model,
            "fallback_used": False,
        }

    def _fallback_chain(self) -> list[str]:
        profile_chain = self.profile.get("fallback_chain", [])
        global_chain = self.config["models"].get("fallback_chain", [])
        seen = {self.preferred_model}
        chain = []
        for candidate in [*profile_chain, *global_chain]:
            if candidate and candidate not in seen:
                seen.add(candidate)
                chain.append(candidate)
        return chain

    async def _resolve_model(self, refresh: bool = False) -> str:
        if self._resolved and not refresh:
            return self.model

        available = []
        active_model = self.preferred_model
        try:
            available = await self.list_models()
        except Exception as exc:
            logger.warning(
                "Could not list local models, using preferred model '%s': %s",
                self.preferred_model,
                exc,
            )
        else:
            if self.preferred_model not in available:
                for candidate in self._fallback_chain():
                    if candidate in available:
                        active_model = candidate
                        break

        self.model = active_model
        self._resolved = True
        self._resolution = {
            "profile": self.profile_name,
            "preferred_model": self.preferred_model,
            "active_model": self.model,
            "fallback_used": self.model != self.preferred_model,
            "fallback_chain": self._fallback_chain(),
            "available_models": available,
        }
        return self.model

    async def describe_resolution(self, refresh: bool = False) -> dict:
        await self._resolve_model(refresh=refresh)
        return dict(self._resolution)

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> dict | AsyncGenerator:
        await self._resolve_model()
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "num_ctx": self.profile.get("num_ctx", 16384),
                "temperature": self.profile.get("temperature", 0.2),
                "top_p": self.profile.get("top_p", 0.9),
                "num_predict": self.profile.get("num_predict", 1024),
            },
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        if stream:
            return self._stream_chat(payload)
        return await self._chat_once(payload)

    async def _chat_once(self, payload: dict, attempt: int = 1) -> dict:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                if status in (500, 502, 503) and attempt < 3:
                    await asyncio.sleep(1.2 if attempt == 1 else 4.0)
                    return await self._chat_once(payload, attempt + 1)
                raise
            except (httpx.ReadTimeout, httpx.ConnectError):
                if attempt < 2:
                    await asyncio.sleep(2.0)
                    return await self._chat_once(payload, attempt + 1)
                raise

            data = resp.json()
            msg = data.get("message", {})
            if isinstance(msg, dict) and "content" in msg:
                msg["content"] = strip_ansi(msg["content"])
                data["message"] = msg
            return data

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = chunk.get("message")
                    if isinstance(msg, dict) and "content" in msg:
                        msg["content"] = strip_ansi(msg["content"])
                        chunk["message"] = msg
                    yield chunk

    async def generate_structured(self, prompt: str, schema: dict, system: Optional[str] = None) -> dict:
        sys_prompt = (
            (system + "\n\n") if system else ""
        ) + (
            "You MUST respond with ONLY valid JSON matching this schema. "
            f"No explanation, no markdown, no backticks.\nSchema: {json.dumps(schema)}"
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat(messages, system=sys_prompt)
        raw = strip_ansi(result.get("message", {}).get("content", ""))
        raw = strip_json_fence(raw)
        if not raw.startswith("{"):
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                raw = match.group(0)
        return json.loads(raw)

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [model["name"] for model in data.get("models", [])]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def pull_model(self, model_name: str) -> AsyncGenerator[str, None]:
        payload = {"name": model_name, "stream": True}
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("POST", f"{self.base_url}/api/pull", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)
