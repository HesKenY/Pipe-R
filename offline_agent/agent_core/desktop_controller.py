"""
agent_core/desktop_controller.py
Mouse, keyboard, and window automation. Mode 3 only.
Uses pyautogui. All actions logged. Kill switch checked before every action.
"""

import time
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger("desktop")

SCREENSHOT_DIR = Path(__file__).parent.parent / "logs" / "screenshots"


class DesktopController:
    """
    Wraps pyautogui for safe desktop automation.
    All actions require Mode 3 permission — enforced by ToolRouter.
    Never call methods here directly; always go through ToolRouter.
    """

    def __init__(self):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self._pyautogui = None  # Lazy import

    def _gui(self):
        if self._pyautogui is None:
            try:
                import pyautogui
                pyautogui.FAILSAFE = True  # Move mouse to corner to abort
                pyautogui.PAUSE = 0.1
                self._pyautogui = pyautogui
            except ImportError:
                raise RuntimeError("pyautogui not installed. Run: pip install pyautogui Pillow")
        return self._pyautogui

    def capture_screen(self, region: Optional[tuple] = None) -> str:
        """
        Take a screenshot. Returns path to saved image.
        region: (x, y, w, h) or None for full screen.
        """
        gui = self._gui()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"screenshot_{ts}.png"
        img = gui.screenshot(region=region)
        img.save(str(path))
        logger.info(f"Screenshot saved: {path}")
        return str(path)

    def move_mouse(self, x: int, y: int, duration: float = 0.3) -> str:
        """Move mouse cursor to (x, y)."""
        self._gui().moveTo(x, y, duration=duration)
        return f"Mouse moved to ({x}, {y})"

    def click(self, button: str = "left", x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Click mouse button. Optionally move to (x, y) first."""
        gui = self._gui()
        if x is not None and y is not None:
            gui.click(x, y, button=button)
        else:
            gui.click(button=button)
        return f"Clicked {button} at ({x}, {y})"

    def double_click(self, x: int, y: int) -> str:
        self._gui().doubleClick(x, y)
        return f"Double-clicked at ({x}, {y})"

    def type_text(self, text: str, delay_ms: int = 50) -> str:
        """Type text via keyboard with optional per-key delay."""
        self._gui().typewrite(text, interval=delay_ms / 1000.0)
        return f"Typed {len(text)} characters"

    def hotkey(self, *keys: str) -> str:
        """Send a keyboard shortcut. Example: hotkey('ctrl', 's')"""
        self._gui().hotkey(*keys)
        return f"Hotkey: {'+'.join(keys)}"

    def get_active_window(self) -> str:
        """Get the title of the currently active window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except ImportError:
            return "pygetwindow not installed"

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Scroll mouse wheel. Positive = up, negative = down."""
        gui = self._gui()
        if x and y:
            gui.scroll(clicks, x=x, y=y)
        else:
            gui.scroll(clicks)
        return f"Scrolled {clicks} clicks"
