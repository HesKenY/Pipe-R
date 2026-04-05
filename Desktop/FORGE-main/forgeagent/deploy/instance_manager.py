"""6-slot multi-model instance manager with cross-referencing."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime
from ..providers.ollama.client import OllamaClient
from ..core.interfaces import ChatMessage
from ..utils.helpers import make_id


class InstanceManager:
    def __init__(self, base_dir: str, ollama_base_url: str):
        self.state_dir = Path(base_dir) / "instances"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.client = OllamaClient(ollama_base_url)
        self.slots: list[dict] = [{"slot": i, "modelName": None, "status": "empty", "lastTask": None, "messagesCount": 0} for i in range(1, 7)]
        self.histories: dict[int, list[ChatMessage]] = {}
        self._load_state()

    def load_model(self, slot: int, model_name: str) -> dict:
        if not 1 <= slot <= 6:
            raise ValueError("Slot must be 1-6")
        s = self.slots[slot - 1]
        s["modelName"] = model_name
        s["status"] = "loaded"
        s["messagesCount"] = 0
        self.histories[slot] = []
        self._save_state()
        return s

    def unload_model(self, slot: int) -> None:
        self.slots[slot - 1] = {"slot": slot, "modelName": None, "status": "empty", "lastTask": None, "messagesCount": 0}
        self.histories.pop(slot, None)
        self._save_state()

    def get_all_slots(self) -> list[dict]:
        return list(self.slots)

    def get_active_slots(self) -> list[dict]:
        return [s for s in self.slots if s["status"] != "empty"]

    async def send_to_slot(self, slot: int, message: str) -> str:
        s = self.slots[slot - 1]
        if not s["modelName"] or s["status"] == "empty":
            raise ValueError(f"Slot {slot} is empty.")
        s["status"] = "busy"
        s["lastTask"] = message[:80]
        self._save_state()
        history = self.histories.get(slot, [])
        if not history:
            history.append(ChatMessage(make_id(), "system", f"You are an AI coding assistant in slot {slot}. Be concise.", datetime.now().isoformat()))
        history.append(ChatMessage(make_id(), "user", message, datetime.now().isoformat()))
        try:
            response = await self.client.chat(model=s["modelName"], messages=history, temperature=0.7)
            history.append(ChatMessage(make_id(), "assistant", response, datetime.now().isoformat()))
            self.histories[slot] = history
            s["status"] = "loaded"
            s["messagesCount"] = len(history)
            self._save_state()
            return response
        except Exception as e:
            s["status"] = "error"
            self._save_state()
            raise

    async def broadcast(self, message: str) -> dict[int, str]:
        results = {}
        for s in self.get_active_slots():
            try:
                results[s["slot"]] = await self.send_to_slot(s["slot"], message)
            except Exception as e:
                results[s["slot"]] = f"Error: {e}"
        return results

    async def coordinate_work(self, task: str) -> dict[int, str]:
        active = self.get_active_slots()
        if not active:
            raise ValueError("No active slots.")
        model = active[0]["modelName"]
        slot_desc = "\n".join(f"Slot {s['slot']}: {s['modelName']}" for s in active)
        plan_prompt = f"Split this task across {len(active)} slots:\n{slot_desc}\n\nTask: {task}\n\nRespond with JSON: [{{'slot': N, 'task': '...'}}]"
        plan = await self.client.chat(model=model,
            messages=[ChatMessage(make_id(), "user", plan_prompt, datetime.now().isoformat())], temperature=0.3)
        assignments: dict[int, str] = {}
        try:
            match = re.search(r"\[[\s\S]*?\]", plan)
            if match:
                for item in json.loads(match.group(0)):
                    if any(s["slot"] == item["slot"] for s in active):
                        assignments[item["slot"]] = item["task"]
        except Exception:
            assignments[active[0]["slot"]] = task
        results = {}
        for slot, subtask in assignments.items():
            try:
                results[slot] = await self.send_to_slot(slot, subtask)
            except Exception as e:
                results[slot] = f"Error: {e}"
        return results

    async def cross_reference(self) -> dict:
        active = self.get_active_slots()
        contexts = []
        for s in active:
            history = self.histories.get(s["slot"], [])
            files = set()
            for m in history:
                found = re.findall(r"[\w./\\-]+\.(?:py|ts|js|go|rs|java|json|yaml|md|tsx|jsx|css|html)", m.content)
                files.update(found)
            contexts.append({"slot": s["slot"], "files": list(files)})
        conflicts = []
        synergies = []
        for i in range(len(contexts)):
            for j in range(i + 1, len(contexts)):
                shared = set(contexts[i]["files"]) & set(contexts[j]["files"])
                for f in shared:
                    conflicts.append({"slot1": contexts[i]["slot"], "slot2": contexts[j]["slot"], "file": f,
                                      "description": f"Both slots working on {f}"})
        return {"conflicts": conflicts, "synergies": synergies}

    def get_slot_history(self, slot: int) -> list[ChatMessage]:
        return self.histories.get(slot, [])

    def clear_slot_history(self, slot: int) -> None:
        self.histories[slot] = []
        self.slots[slot - 1]["messagesCount"] = 0
        self.slots[slot - 1]["lastTask"] = None
        self._save_state()

    def _save_state(self) -> None:
        (self.state_dir / "state.json").write_text(json.dumps({"slots": self.slots}, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        sp = self.state_dir / "state.json"
        if sp.exists():
            try:
                data = json.loads(sp.read_text())
                for i, s in enumerate(data.get("slots", [])[:6]):
                    self.slots[i].update(s)
                    if not self.slots[i].get("modelName"):
                        self.slots[i]["status"] = "empty"
            except Exception:
                pass
