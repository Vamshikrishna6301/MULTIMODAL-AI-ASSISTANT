from __future__ import annotations

import ctypes
import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass
class NVDAReadResult:
    """Normalized result for NVDA-assisted screen reading."""

    spoken_message: str
    source: str
    used_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class NVDAControllerClient:
    """
    Thin ctypes wrapper around nvdaControllerClient.dll.

    Supported exports are intentionally minimal and optional:
    - nvdaController_testIfRunning
    - nvdaController_speakText
    - nvdaController_cancelSpeech
    """

    DLL_CANDIDATES = (
        "nvdaControllerClient64.dll",
        "nvdaControllerClient32.dll",
        "nvdaControllerClient.dll",
        str(Path("execution") / "accessibility" / "nvdaControllerClient64.dll"),
        str(Path("execution") / "accessibility" / "nvdaControllerClient.dll"),
        r"C:\Program Files\NVDA\nvdaControllerClient64.dll",
        r"C:\Program Files\NVDA\nvdaControllerClient32.dll",
        r"C:\Program Files\NVDA\nvdaControllerClient.dll",
    )

    def __init__(self):
        self.dll = None
        self.dll_path: Optional[str] = None
        self._load()

    @property
    def available(self) -> bool:
        return self.dll is not None

    def is_running(self) -> bool:
        if not self.dll:
            return False
        try:
            return int(self.dll.nvdaController_testIfRunning()) == 0
        except Exception:
            return False

    def speak_text(self, text: str) -> bool:
        if not self.dll or not text:
            return False
        try:
            return int(self.dll.nvdaController_speakText(str(text))) == 0
        except Exception:
            return False

    def cancel_speech(self) -> bool:
        if not self.dll:
            return False
        try:
            return int(self.dll.nvdaController_cancelSpeech()) == 0
        except Exception:
            return False

    def _load(self) -> None:
        if os.name != "nt":
            return

        for candidate in self.DLL_CANDIDATES:
            try:
                path = Path(candidate)
                dll_ref = str(path.resolve()) if path.exists() else candidate
                dll = ctypes.WinDLL(dll_ref)
                dll.nvdaController_testIfRunning.restype = ctypes.c_long
                dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                dll.nvdaController_speakText.restype = ctypes.c_long
                dll.nvdaController_cancelSpeech.restype = ctypes.c_long
                self.dll = dll
                self.dll_path = dll_ref
                return
            except Exception:
                continue


class NVDAReader:
    """
    NVDA-assisted screen reader facade.

    This module uses the NVDA controller client for runtime detection and
    optional speech output, while relying on the existing UIA/navigation layer
    for structural extraction. When NVDA is unavailable, it returns a clean
    fallback summary without breaking the existing navigation system.
    """

    ROLE_PRIORITY = ("heading", "button", "link", "input", "tab", "menu", "text", "element")

    def __init__(self, *, cache_ttl_seconds: float = 1.5, duplicate_ttl_seconds: float = 0.8):
        self.controller = NVDAControllerClient()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.duplicate_ttl_seconds = duplicate_ttl_seconds
        self._last_state_key: Optional[str] = None
        self._last_summary: Optional[NVDAReadResult] = None
        self._last_summary_at = 0.0
        self._last_announced_text: Optional[str] = None
        self._last_announced_at = 0.0

    def read_screen(
        self,
        *,
        window_name: str,
        elements: Sequence[Any],
        focused_element: Optional[Any] = None,
        fallback_text: Optional[str] = None,
    ) -> NVDAReadResult:
        state_key = self._screen_state_key(window_name, elements, focused_element)
        cached = self._cached_result(state_key)
        if cached:
            return cached

        normalized = self._normalize_elements(elements)
        if not normalized and focused_element is not None:
            normalized = [self._normalize_element(focused_element)]

        if not normalized:
            message = fallback_text or f"{window_name or 'Current window'} has no readable accessible content."
            return self._finalize(message, source="fallback", state_key=state_key)

        message = self._build_summary(window_name, normalized, focused_element)
        return self._finalize(message, source="nvda_uia_hybrid", state_key=state_key)

    def read_focused_element(
        self,
        *,
        window_name: str,
        focused_element: Optional[Any],
        fallback_text: Optional[str] = None,
        context_label: Optional[str] = None,
    ) -> NVDAReadResult:
        normalized = self._normalize_element(focused_element)
        if not normalized:
            message = fallback_text or "No focused element detected."
            return self._finalize(message, source="fallback")

        prefix = f"{context_label}. " if context_label else ""
        message = f"{prefix}{self._element_phrase(normalized)}"
        return self._finalize(message, source="nvda_focus")

    def available(self) -> bool:
        return self.controller.available

    def running(self) -> bool:
        return self.controller.is_running()

    def _finalize(
        self,
        message: str,
        *,
        source: str,
        state_key: Optional[str] = None,
        used_cache: bool = False,
    ) -> NVDAReadResult:
        message = self._squash_whitespace(message)
        metadata = {
            "nvda_available": self.controller.available,
            "nvda_running": self.controller.is_running(),
            "used_nvda_speech": False,
            "suppress_tts": False,
        }

        if self.controller.available and self.controller.is_running() and not self._is_duplicate_announcement(message):
            if self.controller.speak_text(message):
                metadata["used_nvda_speech"] = True
                metadata["suppress_tts"] = True
                self._last_announced_text = message
                self._last_announced_at = time.time()

        result = NVDAReadResult(
            spoken_message=message,
            source=source,
            used_cache=used_cache,
            metadata=metadata,
        )

        if state_key:
            self._last_state_key = state_key
            self._last_summary = result
            self._last_summary_at = time.time()

        return result

    def _cached_result(self, state_key: str) -> Optional[NVDAReadResult]:
        if (
            self._last_summary
            and self._last_state_key == state_key
            and (time.time() - self._last_summary_at) <= self.cache_ttl_seconds
        ):
            return NVDAReadResult(
                spoken_message=self._last_summary.spoken_message,
                source=self._last_summary.source,
                used_cache=True,
                metadata=dict(self._last_summary.metadata),
            )
        return None

    def _screen_state_key(
        self,
        window_name: str,
        elements: Sequence[Any],
        focused_element: Optional[Any],
    ) -> str:
        parts = [window_name or ""]
        for element in list(elements)[:20]:
            normalized = self._normalize_element(element)
            if normalized:
                parts.append(f"{normalized['role']}:{normalized['name']}")
        focused = self._normalize_element(focused_element)
        if focused:
            parts.append(f"focus:{focused['role']}:{focused['name']}")
        digest = hashlib.sha1("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()
        return digest

    def _normalize_elements(self, elements: Iterable[Any]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        seen = set()

        for element in elements:
            item = self._normalize_element(element)
            if not item:
                continue
            key = (item["role"], item["name"])
            if key in seen:
                continue
            seen.add(key)
            normalized.append(item)

        return normalized

    def _normalize_element(self, element: Optional[Any]) -> Optional[Dict[str, str]]:
        if element is None:
            return None

        name = (getattr(element, "name", None) or "").strip()
        role = (
            getattr(element, "control_type", None)
            or getattr(element, "role", None)
            or getattr(element, "element_type", None)
            or "Element"
        )
        role = self._normalize_role(str(role))

        if not name and role == "text":
            return None

        if not name:
            name = "Unnamed"

        return {"name": name, "role": role}

    def _normalize_role(self, role: str) -> str:
        value = role.lower().strip()
        if "heading" in value:
            return "heading"
        if "button" in value:
            return "button"
        if "link" in value or "hyperlink" in value:
            return "link"
        if value in {"edit", "textbox", "input", "input field"} or "input" in value:
            return "input"
        if "tab" in value:
            return "tab"
        if "menu" in value:
            return "menu"
        if value in {"text", "document"}:
            return "text"
        return "element"

    def _build_summary(
        self,
        window_name: str,
        elements: Sequence[Dict[str, str]],
        focused_element: Optional[Any],
    ) -> str:
        groups: Dict[str, List[str]] = {role: [] for role in self.ROLE_PRIORITY}
        for item in elements:
            groups.setdefault(item["role"], []).append(item["name"])

        lines = [f"In {window_name or 'the current window'}."]

        focused = self._normalize_element(focused_element)
        if focused:
            lines.append(f"Focused {self._element_phrase(focused)}.")

        for role in self.ROLE_PRIORITY:
            names = groups.get(role) or []
            if not names:
                continue
            unique_names = self._unique_preserve_order(names)
            count = len(unique_names)
            sample = ", ".join(unique_names[:3])
            label = self._role_label(role, count)
            if count <= 3:
                lines.append(f"{count} {label}: {sample}.")
            else:
                lines.append(f"{count} {label}, including {sample}.")

        return " ".join(lines[:8])

    def _role_label(self, role: str, count: int) -> str:
        base = {
            "heading": "heading",
            "button": "button",
            "link": "link",
            "input": "input field",
            "tab": "tab",
            "menu": "menu item",
            "text": "text item",
            "element": "interactive element",
        }.get(role, "element")
        if count == 1:
            return base
        if base.endswith("y"):
            return base[:-1] + "ies"
        if base.endswith("x"):
            return base + "es"
        return base + "s"

    def _element_phrase(self, item: Dict[str, str]) -> str:
        role = self._role_label(item["role"], 1)
        return f"{role}: {item['name']}"

    def _unique_preserve_order(self, values: Sequence[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(value)
        return result

    def _is_duplicate_announcement(self, text: str) -> bool:
        return (
            self._last_announced_text == text
            and (time.time() - self._last_announced_at) <= self.duplicate_ttl_seconds
        )

    def _squash_whitespace(self, text: str) -> str:
        return " ".join((text or "").split()).strip()
