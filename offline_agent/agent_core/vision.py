"""
agent_core/vision.py
Screenshot understanding using local vision model (llava via Ollama).
Mode 2+ for capture, model inference always local.
"""

import base64
import httpx
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("vision")

OLLAMA_URL = "http://localhost:11434"


class Vision:
    """
    Sends screenshots or images to a local vision model for understanding.
    Uses llava or similar multimodal model via Ollama.
    """

    def __init__(self, model: str = "llava:13b"):
        self.model = model

    async def describe_image(self, image_path: str, prompt: str = "Describe what you see.") -> str:
        """Send an image to the local vision model and get a description."""
        path = Path(image_path)
        if not path.exists():
            return f"Image not found: {image_path}"

        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_b64],
                }
            ],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "No response from vision model")
        except Exception as e:
            return f"Vision model error: {e}"

    async def read_screen_text(self, image_path: str) -> str:
        """Extract text visible in a screenshot."""
        return await self.describe_image(
            image_path,
            "Extract and return all text visible in this screenshot. Format it cleanly."
        )

    async def find_ui_element(self, image_path: str, element_description: str) -> str:
        """Ask model to locate a UI element and describe its position."""
        return await self.describe_image(
            image_path,
            f"In this screenshot, find the UI element described as: '{element_description}'. "
            "Describe its approximate location (top-left, center, coordinates if visible)."
        )

    async def analyze_error(self, image_path: str) -> str:
        """Analyze a screenshot for error messages or problems."""
        return await self.describe_image(
            image_path,
            "Look for any error messages, warnings, or problems in this screenshot. "
            "Report what you find and what the likely cause is."
        )
