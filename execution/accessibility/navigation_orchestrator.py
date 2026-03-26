from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

from infrastructure.logger import get_logger


@dataclass
class NavigationCommand:
    """Normalized command passed into the navigation orchestrator."""

    action: str
    semantic_type: Optional[str] = None
    refresh: bool = False
    max_items: int = 10


@dataclass
class NavigationSnapshot:
    """Cached accessibility snapshot for a single window."""

    window_name: str
    elements: List[Any]
    focused_element: Optional[Any] = None
    source: str = "scan"
    created_at: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    stable_focus: bool = False

    @property
    def element_count(self) -> int:
        return len(self.elements)


@dataclass
class NavigationResult:
    """Outcome returned by the orchestrator."""

    success: bool
    spoken_message: str
    strategy: str
    confidence: float
    latency_ms: float
    element: Optional[Any] = None
    elements: Optional[List[Any]] = None
    snapshot: Optional[NavigationSnapshot] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NavigationSnapshotCache:
    """Thread-safe cache that keeps the latest snapshot per active window."""

    def __init__(self, ttl_seconds: float = 1.5):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._window_name: Optional[str] = None
        self._snapshot: Optional[NavigationSnapshot] = None

    def get(self, window_name: Optional[str]) -> Optional[NavigationSnapshot]:
        if not window_name:
            return None
        with self._lock:
            if self._window_name != window_name or self._snapshot is None:
                return None
            age = time.time() - self._snapshot.created_at
            if age > self.ttl_seconds:
                return None
            return self._snapshot

    def set(self, snapshot: NavigationSnapshot) -> None:
        with self._lock:
            self._window_name = snapshot.window_name
            self._snapshot = snapshot

    def invalidate(self) -> None:
        with self._lock:
            self._window_name = None
            self._snapshot = None


class NavigationOrchestrator:
    """
    Central navigation controller that chooses between focus, keyboard,
    and UI scan strategies at runtime.
    """

    def __init__(
        self,
        *,
        state: Any,
        cache: Optional[NavigationSnapshotCache] = None,
        window_provider: Optional[Callable[[], str]] = None,
        focus_provider: Optional[Callable[[], Optional[Any]]] = None,
        scanner: Optional[Callable[[], tuple[str, List[Any]]]] = None,
        announcer: Optional[Callable[[str], Optional[str]]] = None,
        keyboard_next: Optional[Callable[[bool], Optional[Any]]] = None,
        keyboard_activate: Optional[Callable[[], bool]] = None,
        focus_setter: Optional[Callable[[Any], bool]] = None,
    ):
        self.logger = get_logger("accessibility.navigation_orchestrator")
        self.state = state
        self.cache = cache or NavigationSnapshotCache()
        self.window_provider = window_provider or (lambda: "")
        self.focus_provider = focus_provider or (lambda: None)
        self.scanner = scanner or (lambda: ("", []))
        self.announcer = announcer or (lambda text: text)
        self.keyboard_next = keyboard_next
        self.keyboard_activate = keyboard_activate
        self.focus_setter = focus_setter or self._default_focus_setter

    def execute(self, command: NavigationCommand) -> NavigationResult:
        start = time.perf_counter()
        strategies = self._strategy_order(command)
        attempted: List[str] = []

        for strategy in strategies:
            attempted.append(strategy)
            result = self._run_strategy(strategy, command)
            if result and result.success:
                result.metadata.setdefault("attempted_strategies", attempted)
                result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
                return result

        return NavigationResult(
            success=False,
            spoken_message="No accessible target found.",
            strategy="none",
            confidence=0.0,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
            metadata={"attempted_strategies": attempted},
        )

    def refresh(self) -> NavigationSnapshot:
        window_name, elements = self.scanner()
        focused = self.focus_provider()
        snapshot = NavigationSnapshot(
            window_name=window_name or "Unknown window",
            elements=elements or [],
            focused_element=focused,
            source="scan",
            latency_ms=0.0,
            stable_focus=focused is not None,
        )
        self.cache.set(snapshot)
        self.state.load(snapshot.window_name, snapshot.elements)
        if focused is not None:
            self.state.set_focused(focused)
        return snapshot

    def _strategy_order(self, command: NavigationCommand) -> List[str]:
        if command.action in {"read_screen", "refresh"}:
            return ["focus", "scan", "keyboard"]
        if command.action in {"activate", "read_current"}:
            return ["focus", "keyboard", "scan"]
        return ["focus", "keyboard", "scan"]

    def _run_strategy(
        self, strategy: str, command: NavigationCommand
    ) -> Optional[NavigationResult]:
        if strategy == "focus":
            return self._run_focus_strategy(command)
        if strategy == "keyboard":
            return self._run_keyboard_strategy(command)
        if strategy == "scan":
            return self._run_scan_strategy(command)
        return None

    def _run_focus_strategy(self, command: NavigationCommand) -> Optional[NavigationResult]:
        focused = self.focus_provider()
        if focused is None:
            return None

        current_window = self.window_provider() or getattr(self.state, "window", "") or "Unknown window"
        cached_snapshot = self.cache.get(current_window)
        if cached_snapshot and getattr(cached_snapshot, "elements", None):
            self.state.load(current_window, cached_snapshot.elements)
        self.state.set_focused(focused)

        if command.action == "read_current":
            speech = self._describe(focused)
            return self._success("focus", speech, focused, confidence=0.96, snapshot=cached_snapshot)

        if command.action == "activate":
            activated = self._activate_element(focused)
            if not activated:
                return None
            speech = f"Activated {self._describe(focused)}"
            return self._success("focus", speech, focused, confidence=0.93, snapshot=cached_snapshot)

        if command.action == "focus_input" and self._matches_semantic(focused, "input"):
            return self._success("focus", f"Focused {self._describe(focused)}", focused, confidence=0.95, snapshot=cached_snapshot)

        if command.action == "semantic_next" and command.semantic_type and self._matches_semantic(
            focused, command.semantic_type
        ):
            return self._success("focus", self._describe(focused), focused, confidence=0.88, snapshot=cached_snapshot)

        if command.action in {"next", "previous"} and cached_snapshot and cached_snapshot.elements:
            return self._move_with_cached_elements(
                command,
                cached_snapshot,
                strategy="focus",
                confidence=0.82,
            )

        return None

    def _run_keyboard_strategy(self, command: NavigationCommand) -> Optional[NavigationResult]:
        current_window = self.window_provider() or getattr(self.state, "window", "") or "Unknown window"
        snapshot = self.cache.get(current_window)

        if snapshot and snapshot.elements:
            return self._move_with_cached_elements(
                command,
                snapshot,
                strategy="keyboard",
                confidence=0.78,
            )

        if command.action == "semantic_next" and command.semantic_type and self.keyboard_next:
            element = self._tab_until_semantic(command.semantic_type, reverse=False, attempts=10)
            if element is None:
                return None
            self.state.set_focused(element)
            return self._success(
                "keyboard",
                self._describe(element),
                element,
                confidence=0.74,
                snapshot=snapshot,
            )

        if command.action == "focus_input" and self.keyboard_next:
            element = self._tab_until_semantic("input", reverse=False, attempts=10)
            if element is None:
                return None
            self.state.set_focused(element)
            return self._success(
                "keyboard",
                f"Focused {self._describe(element)}",
                element,
                confidence=0.74,
                snapshot=snapshot,
            )

        if command.action in {"next", "previous"} and self.keyboard_next:
            reverse = command.action == "previous"
            element = self.keyboard_next(reverse)
            if element is None:
                return None
            self.state.set_focused(element)
            speech = self._describe(element)
            return self._success("keyboard", speech, element, confidence=0.72, snapshot=snapshot)

        if command.action == "activate" and self.keyboard_activate:
            if not self.keyboard_activate():
                return None
            focused = self.focus_provider()
            speech = "Activated current element."
            if focused is not None:
                speech = f"Activated {self._describe(focused)}"
            return self._success("keyboard", speech, focused, confidence=0.7, snapshot=snapshot)

        return None

    def _run_scan_strategy(self, command: NavigationCommand) -> Optional[NavigationResult]:
        scan_start = time.perf_counter()
        snapshot = self.refresh()
        snapshot.latency_ms = round((time.perf_counter() - scan_start) * 1000, 2)

        if command.action in {"read_screen", "refresh"}:
            message = self._build_read_screen_message(snapshot, command.max_items)
            confidence = self._snapshot_confidence(snapshot, base=0.9)
            return self._success(
                "scan",
                message,
                snapshot.focused_element,
                confidence=confidence,
                snapshot=snapshot,
                elements=snapshot.elements,
            )

        if command.action == "read_current" and snapshot.focused_element is not None:
            return self._success(
                "scan",
                self._describe(snapshot.focused_element),
                snapshot.focused_element,
                confidence=self._snapshot_confidence(snapshot, base=0.84),
                snapshot=snapshot,
            )

        if command.action == "activate":
            current = self.state.current()
            if current is None:
                return None
            activated = self._activate_element(current)
            if not activated:
                return None
            return self._success(
                "scan",
                f"Activated {self._describe(current)}",
                current,
                confidence=self._snapshot_confidence(snapshot, base=0.86),
                snapshot=snapshot,
            )

        if command.action == "focus_input":
            element = self._find_first(snapshot.elements, lambda item: self._matches_semantic(item, "input"))
            if element is None:
                return None
            self.focus_setter(element)
            return self._success(
                "scan",
                f"Focused {self._describe(element)}",
                element,
                confidence=self._snapshot_confidence(snapshot, base=0.83),
                snapshot=snapshot,
            )

        if command.action == "semantic_next" and command.semantic_type:
            return self._move_with_cached_elements(
                command,
                snapshot,
                strategy="scan",
                confidence=self._snapshot_confidence(snapshot, base=0.81),
            )

        if command.action in {"next", "previous"}:
            return self._move_with_cached_elements(
                command,
                snapshot,
                strategy="scan",
                confidence=self._snapshot_confidence(snapshot, base=0.8),
            )

        return None

    def _move_with_cached_elements(
        self,
        command: NavigationCommand,
        snapshot: NavigationSnapshot,
        *,
        strategy: str,
        confidence: float,
    ) -> Optional[NavigationResult]:
        elements = snapshot.elements or []
        if not elements:
            return None

        if command.action == "next":
            element = self.state.next()
        elif command.action == "previous":
            element = self.state.previous()
        elif command.action == "semantic_next" and command.semantic_type:
            element = self.state.find_next(lambda item: self._matches_semantic(item, command.semantic_type or ""))
        else:
            element = None

        if element is None and command.action == "focus_input":
            element = self._find_first(elements, lambda item: self._matches_semantic(item, "input"))

        if element is None:
            return None

        self.focus_setter(element)
        element_name = getattr(element, "name", None) or "Unnamed"
        self.logger.info(
            "NAVIGATION_MOVED",
            action=command.action,
            element_name=element_name,
            strategy=strategy,
        )
        return self._success(
            strategy,
            f"Focused: {element_name}",
            element,
            confidence=confidence,
            snapshot=snapshot,
            elements=elements,
        )

    def _build_read_screen_message(self, snapshot: NavigationSnapshot, max_items: int) -> str:
        if not snapshot.elements:
            if snapshot.focused_element is not None:
                return f"You are in {snapshot.window_name}. Focused {self._describe(snapshot.focused_element)}."
            return f"You are in {snapshot.window_name}."

        lines = [f"You are in {snapshot.window_name}."]
        for element in snapshot.elements[:max_items]:
            text = self.announcer(self._describe(element))
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _snapshot_confidence(self, snapshot: NavigationSnapshot, *, base: float) -> float:
        confidence = base
        if snapshot.element_count == 0:
            confidence -= 0.45
        elif snapshot.element_count < 4:
            confidence -= 0.08
        if snapshot.latency_ms > 900:
            confidence -= 0.1
        if snapshot.stable_focus:
            confidence += 0.03
        return max(0.0, min(0.99, round(confidence, 2)))

    def _success(
        self,
        strategy: str,
        spoken_message: str,
        element: Optional[Any],
        *,
        confidence: float,
        snapshot: Optional[NavigationSnapshot],
        elements: Optional[List[Any]] = None,
    ) -> NavigationResult:
        return NavigationResult(
            success=True,
            spoken_message=spoken_message,
            strategy=strategy,
            confidence=max(0.0, min(0.99, round(confidence, 2))),
            latency_ms=0.0,
            element=element,
            elements=elements,
            snapshot=snapshot,
            metadata={"window": getattr(snapshot, "window_name", None)},
        )

    def _find_first(self, elements: Iterable[Any], predicate: Callable[[Any], bool]) -> Optional[Any]:
        for element in elements:
            try:
                if predicate(element):
                    return element
            except Exception:
                continue
        return None

    def _describe(self, element: Any) -> str:
        if element is None:
            return "Unknown element"
        speakable = getattr(element, "speakable", None)
        if callable(speakable):
            try:
                return speakable()
            except Exception:
                pass
        role = getattr(element, "control_type", None) or getattr(element, "role", None) or "Element"
        name = getattr(element, "name", None) or "Unnamed"
        return f"{role} {name}".strip()

    def _matches_semantic(self, element: Any, semantic_type: str) -> bool:
        semantic_type = semantic_type.lower()
        if semantic_type == "input":
            checker = getattr(element, "is_input", None)
            return bool(checker()) if callable(checker) else "edit" in self._describe(element).lower()
        if semantic_type == "button":
            checker = getattr(element, "is_button", None)
            return bool(checker()) if callable(checker) else "button" in self._describe(element).lower()
        if semantic_type == "link":
            checker = getattr(element, "is_link", None)
            return bool(checker()) if callable(checker) else "link" in self._describe(element).lower()
        if semantic_type == "tab":
            return "tab" in self._describe(element).lower()
        if semantic_type == "menu":
            return "menu" in self._describe(element).lower()
        if semantic_type == "chat":
            return "chat" in self._describe(element).lower() or getattr(element, "region", None) == "sidebar"
        if semantic_type == "message":
            return "message" in self._describe(element).lower() or getattr(element, "region", None) == "main"
        return False

    def _tab_until_semantic(self, semantic_type: str, *, reverse: bool, attempts: int) -> Optional[Any]:
        if not self.keyboard_next:
            return None
        for _ in range(max(0, attempts)):
            element = self.keyboard_next(reverse)
            if element is None:
                continue
            try:
                if self._matches_semantic(element, semantic_type):
                    return element
            except Exception:
                continue
        return None

    def _activate_element(self, element: Any) -> bool:
        if element is None:
            return False
        invoker = getattr(element, "click", None)
        if callable(invoker):
            try:
                invoker()
                return True
            except Exception:
                return False
        return False

    def _default_focus_setter(self, element: Any) -> bool:
        setter = getattr(element, "set_focus", None)
        if callable(setter):
            try:
                setter()
                return True
            except Exception:
                return False
        return False
