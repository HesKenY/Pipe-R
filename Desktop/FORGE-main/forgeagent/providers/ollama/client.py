"""Ollama HTTP client with streaming and speed optimizations."""
from __future__ import annotations
import json
from typing import AsyncIterator
import httpx
from ...core.interfaces import ChatMessage


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        out = []
        for m in messages:
            if m.role == "tool":
                out.append({"role": "user", "content": f"[Tool Result: {m.name}]\n{m.content}"})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        num_predict: int = 2048,
    ) -> str:
        body = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": 8192,
                "repeat_penalty": 1.1,
                "top_k": 40,
                "top_p": 0.9,
            },
            "keep_alive": "30m",
        }
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        body = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
                "num_ctx": 8192,
                "repeat_penalty": 1.1,
                "top_k": 40,
                "top_p": 0.9,
            },
            "keep_alive": "30m",
        }
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
