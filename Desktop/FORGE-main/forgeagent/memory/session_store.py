"""Session persistence and memory/dreams."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from ..core.interfaces import ChatMessage
from ..utils.helpers import ensure_dir, write_json, read_json, base36_now


class SessionStore:
    def __init__(self, directory: str):
        self.dir = Path(directory)
        ensure_dir(self.dir)

    async def save(self, messages: list[ChatMessage]) -> str:
        sid = base36_now()
        write_json(self.dir / f"session-{sid}.json", {
            "id": sid, "saved": datetime.now().isoformat(),
            "messageCount": len(messages),
            "history": [self._ser(m) for m in messages],
        })
        return sid

    async def overwrite_latest(self, messages: list[ChatMessage]) -> None:
        write_json(self.dir / "latest.json", {
            "saved": datetime.now().isoformat(),
            "messageCount": len(messages),
            "history": [self._ser(m) for m in messages],
        })

    async def load_latest(self) -> list[ChatMessage] | None:
        data = read_json(self.dir / "latest.json")
        if data and isinstance(data, dict):
            return [self._deser(m) for m in data.get("history", [])]
        return None

    def list_all(self) -> list[dict]:
        results = []
        for f in sorted(self.dir.glob("session-*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                first_user = next((m for m in data.get("history", []) if m.get("role") == "user"), None)
                results.append({
                    "id": data.get("id", f.stem.replace("session-", "")),
                    "date": data.get("saved", ""),
                    "msgs": data.get("messageCount", 0),
                    "preview": (first_user or {}).get("content", "(empty)")[:60],
                })
            except Exception:
                pass
        return results

    @staticmethod
    def _ser(m: ChatMessage) -> dict:
        return {"id": m.id, "role": m.role, "content": m.content, "timestamp": m.timestamp, "name": m.name}

    @staticmethod
    def _deser(d: dict) -> ChatMessage:
        return ChatMessage(id=d.get("id", ""), role=d.get("role", ""), content=d.get("content", ""),
                           timestamp=d.get("timestamp", ""), name=d.get("name"))


class MemoryStore:
    def __init__(self, memory_dir: str, dreams_dir: str):
        self.mem_file = Path(memory_dir) / "MEMORY.md"
        self.dreams_dir = Path(dreams_dir)
        Path(memory_dir).mkdir(parents=True, exist_ok=True)
        self.dreams_dir.mkdir(parents=True, exist_ok=True)
        if not self.mem_file.exists():
            self.mem_file.write_text("# ForgeAgent Memory\n\n", encoding="utf-8")

    def read(self) -> str:
        return self.mem_file.read_text(encoding="utf-8")

    def get_context(self, max_chars: int = 10000) -> str:
        full = self.read()
        return full if len(full) <= max_chars else "...(truncated)...\n" + full[-max_chars:]

    def append(self, section: str, content: str) -> None:
        with open(self.mem_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {section} — {datetime.now().isoformat()}\n{content}\n")

    async def dream(self, summarize, history: list[ChatMessage]) -> str | None:
        if len(history) < 4:
            return None
        transcript = "\n".join(
            f"[{m.role}] {m.content[:500]}" for m in history if m.role in ("user", "assistant")
        )
        summary = await summarize(
            "Summarize this conversation into concise bullet points for long-term memory. "
            "Focus on: decisions made, facts learned, code written, user preferences, unresolved tasks.\n\n"
            + transcript
        )
        ts = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        (self.dreams_dir / f"dream-{ts}.md").write_text(f"# Dream — {ts}\n\n{summary}\n", encoding="utf-8")
        self.append("Dream", summary)
        return summary

    def stats(self) -> dict:
        size = self.mem_file.stat().st_size if self.mem_file.exists() else 0
        dreams = list(self.dreams_dir.glob("*.md"))
        return {
            "size_kb": f"{size / 1024:.1f}",
            "dreams": len(dreams),
            "last_dream": dreams[-1].name if dreams else None,
        }
