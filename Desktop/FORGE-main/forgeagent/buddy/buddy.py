"""Tamagotchi companion system."""
from __future__ import annotations
import json
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


QUIPS = {
    "happy": ["Ready to code!", "Let's build something cool!", "Feeling productive!"],
    "excited": ["LEVEL UP!", "New powers unlocked!", "I'm evolving!"],
    "sleeping": ["*yawn* ...still here...", "zzz..."],
    "tired": ["Could use a break...", "Running low..."],
    "hungry": ["Feed me some code!", "Give me a challenge!"],
    "proud": ["Look how far we've come!", "Great team!"],
    "neutral": ["What are we working on?", "Standing by."],
}


@dataclass
class BuddySummary:
    name: str
    level: int
    xp: int
    xp_to_next: int
    energy: int
    mood: str
    total_interactions: int
    achievements: int


class Buddy:
    def __init__(self, buddy_dir: str):
        Path(buddy_dir).mkdir(parents=True, exist_ok=True)
        self.file_path = Path(buddy_dir) / "buddy.json"
        self.data = self._load()

    def _load(self) -> dict:
        defaults = {
            "name": "Sparky", "level": 1, "xp": 0, "xp_to_next": 100,
            "energy": 100, "mood": "happy",
            "created": datetime.now().isoformat(),
            "last_interaction": datetime.now().isoformat(),
            "total_interactions": 0, "tools_used": 0,
            "dreams_witnessed": 0, "achievements": [],
        }
        if self.file_path.exists():
            try:
                saved = json.loads(self.file_path.read_text())
                defaults.update(saved)
            except Exception:
                pass
        return defaults

    def _save(self):
        self.file_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def on_interaction(self):
        self.data["total_interactions"] += 1
        self.data["xp"] += 5
        self.data["last_interaction"] = datetime.now().isoformat()
        self._update_mood()
        self._check_level_up()
        self._save()

    def on_tool_use(self):
        self.data["tools_used"] += 1
        self.data["xp"] += 3
        self._check_level_up()
        self._save()

    def on_dream(self):
        self.data["dreams_witnessed"] += 1
        self.data["xp"] += 10
        self.data["energy"] = min(100, self.data["energy"] + 20)
        self._check_level_up()
        self._save()

    def _check_level_up(self):
        if self.data["xp"] >= self.data["xp_to_next"]:
            self.data["xp"] -= self.data["xp_to_next"]
            self.data["level"] += 1
            self.data["xp_to_next"] = int(self.data["xp_to_next"] * 1.5)
            self.data["mood"] = "excited"

    def _update_mood(self):
        hour = datetime.now().hour
        energy = self.data["energy"]
        if energy < 20:
            self.data["mood"] = "tired"
        elif 0 <= hour < 5:
            self.data["mood"] = "sleeping"
        elif energy < 50:
            self.data["mood"] = "hungry"
        elif self.data["total_interactions"] % 10 == 0:
            self.data["mood"] = "proud"
        elif energy > 80:
            self.data["mood"] = "happy"
        else:
            self.data["mood"] = "neutral"

    def get_quip(self) -> str:
        quips = QUIPS.get(self.data["mood"], QUIPS["neutral"])
        return random.choice(quips)

    @property
    def summary(self) -> BuddySummary:
        return BuddySummary(
            name=self.data["name"], level=self.data["level"],
            xp=self.data["xp"], xp_to_next=self.data["xp_to_next"],
            energy=self.data["energy"], mood=self.data["mood"],
            total_interactions=self.data["total_interactions"],
            achievements=len(self.data.get("achievements", [])),
        )
