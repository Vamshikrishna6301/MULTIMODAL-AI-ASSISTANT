"""
Safe file operations for Phase 3.
All destructive operations must be explicitly confirmed before calling (no implicit deletes).
"""
import os
from typing import Optional


def read_file(path: str) -> tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)


def write_file(path: str, content: str, dry_run: bool = True) -> Optional[str]:
    if dry_run:
        return f"dry-run: would write {len(content)} bytes to {path}"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return None
    except Exception as e:
        return str(e)


def delete_file(path: str, dry_run: bool = True) -> Optional[str]:
    # Disallow dangerous global patterns
    if "*" in path or path.strip() in ("/", "\\", "C:"):
        return "refused: unsafe delete pattern"
    if dry_run:
        return f"dry-run: would delete {path}"
    try:
        os.remove(path)
        return None
    except Exception as e:
        return str(e)
