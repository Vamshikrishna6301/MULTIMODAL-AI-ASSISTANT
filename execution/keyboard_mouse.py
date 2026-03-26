"""
Keyboard and mouse safe helpers for Phase 3.
Uses `pyautogui` for GUI interactions. Functions are intentionally small and provide a `dry_run` switch.
"""
import time
from typing import Optional

try:
    import pyautogui
except Exception:
    pyautogui = None


def type_text(text: str, interval: float = 0.01, dry_run: bool = True) -> Optional[str]:
    """Type text into the active window. If dry_run True, returns simulated output."""
    if dry_run:
        return f"dry-run: would type '{text}'"
    if pyautogui is None:
        return "pyautogui not available"
    try:
        pyautogui.write(text, interval=interval)
        return None
    except Exception as e:
        return str(e)


def press_key(key: str, dry_run: bool = True) -> Optional[str]:
    if dry_run:
        return f"dry-run: would press '{key}'"
    if pyautogui is None:
        return "pyautogui not available"
    try:
        pyautogui.press(key)
        return None
    except Exception as e:
        return str(e)


def click(x: int, y: int, clicks: int = 1, interval: float = 0.0, dry_run: bool = True) -> Optional[str]:
    if dry_run:
        return f"dry-run: would click at ({x},{y}) {clicks}x"
    if pyautogui is None:
        return "pyautogui not available"
    try:
        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval)
        return None
    except Exception as e:
        return str(e)


def move_to(x: int, y: int, duration: float = 0.2, dry_run: bool = True) -> Optional[str]:
    if dry_run:
        return f"dry-run: would move to ({x},{y})"
    if pyautogui is None:
        return "pyautogui not available"
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return None
    except Exception as e:
        return str(e)
