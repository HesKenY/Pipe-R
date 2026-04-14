"""
tools/ui_tools.py
Desktop UI tool wrappers. All require Mode 3 via ToolRouter.
These are thin shims over DesktopController — never call directly.
"""

from agent_core.desktop_controller import DesktopController
from agent_core.vision import Vision

_desktop = DesktopController()
_vision = Vision()


def capture_screen(region: list = None) -> str:
    """Take a screenshot. Returns file path."""
    r = tuple(region) if region else None
    return _desktop.capture_screen(region=r)


def move_mouse(x: int, y: int) -> str:
    return _desktop.move_mouse(x, y)


def click(button: str = "left", x: int = None, y: int = None) -> str:
    return _desktop.click(button=button, x=x, y=y)


def double_click(x: int, y: int) -> str:
    return _desktop.double_click(x, y)


def type_text(text: str, delay_ms: int = 50) -> str:
    return _desktop.type_text(text, delay_ms=delay_ms)


def hotkey(keys: list[str]) -> str:
    return _desktop.hotkey(*keys)


def get_active_window() -> str:
    return _desktop.get_active_window()


def scroll(clicks: int, x: int = None, y: int = None) -> str:
    return _desktop.scroll(clicks, x=x, y=y)


async def describe_screenshot(image_path: str, prompt: str = "Describe what you see.") -> str:
    """Send a screenshot to the local vision model."""
    return await _vision.describe_image(image_path, prompt)


async def read_screen_text(image_path: str) -> str:
    """Extract text from a screenshot using vision model."""
    return await _vision.read_screen_text(image_path)


async def find_ui_element(image_path: str, element_description: str) -> str:
    """Locate a UI element in a screenshot."""
    return await _vision.find_ui_element(image_path, element_description)
