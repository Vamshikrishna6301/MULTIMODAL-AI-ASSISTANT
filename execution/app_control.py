"""
App control helpers for Phase 3
- open_app(app_name): opens a safe, whitelisted application
- close_app(app_name): attempts to gracefully close an app

This module uses OS-appropriate commands and keeps a safety-first whitelist.
"""
import os
import subprocess
import platform
from typing import Optional

# Whitelist of apps and their safe launch commands
APP_WHITELIST = {
    "chrome": {
        "win": lambda: subprocess.Popen(["start", "chrome"], shell=True),
        "default": lambda: subprocess.Popen(["google-chrome"]),
    },
    "notepad": {
        "win": lambda: subprocess.Popen(["notepad"]),
    },
    "calculator": {
        "win": lambda: subprocess.Popen(["calc"]),
    },
    "explorer": {
        "win": lambda: subprocess.Popen(["explorer"]),
    },
    "whatsapp": {
        "win": lambda: subprocess.Popen(["whatsapp"]),
    },
}


def _platform_key() -> str:
    sys = platform.system().lower()
    if sys.startswith("win"):
        return "win"
    return "default"


def open_app(app_name: str) -> Optional[str]:
    """Open a whitelisted application. Returns None on success or error string."""
    key = app_name.lower()
    if key not in APP_WHITELIST:
        return f"App '{app_name}' not whitelisted"

    plat = _platform_key()
    cmd = APP_WHITELIST[key].get(plat) or APP_WHITELIST[key].get("default")
    if not cmd:
        return f"No launch command for '{app_name}' on platform {plat}"

    try:
        cmd()
        return None
    except Exception as e:
        return str(e)


def close_app(app_name: str) -> Optional[str]:
    """Attempt to close application by name. Best-effort; returns error string on failure."""
    key = app_name.lower()
    plat = _platform_key()
    try:
        if plat == "win":
            # Use taskkill for Windows
            subprocess.run(["taskkill", "/IM", f"{key}.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return None
        else:
            # Generic pkill
            subprocess.run(["pkill", "-f", key], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return None
    except Exception as e:
        return str(e)
