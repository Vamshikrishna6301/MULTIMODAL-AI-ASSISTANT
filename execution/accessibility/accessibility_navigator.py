from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import re
import threading
import time
from typing import Any, List, Optional, Tuple

from execution.accessibility.navigation_orchestrator import (
    NavigationCommand,
    NavigationOrchestrator,
    NavigationSnapshotCache,
)
from execution.accessibility.accessibility_tree import AccessibilityTree
from execution.accessibility.accessibility_tree_builder import AccessibilityTreeBuilder
from execution.accessibility.nvda_reader import NVDAReader
from execution.accessibility.navigation_state import NavigationState
from execution.accessibility.output_filter import OutputFilter
from execution.accessibility.semantic_screen_analyzer import SemanticScreenAnalyzer
from execution.accessibility.ui_element import UIElement
from infrastructure.uia_dispatcher import dispatcher
from infrastructure.logger import get_logger

try:
    import win32gui
except Exception:  # pragma: no cover - import safety for non-Windows tests
    win32gui = None

try:
    from pywinauto import Application, Desktop
except Exception:  # pragma: no cover - import safety for non-Windows tests
    Application = None
    Desktop = None

try:
    from pywinauto.keyboard import send_keys
except Exception:  # pragma: no cover - import safety for non-Windows tests
    send_keys = None


class UIElementWrapper:
    """Stable adapter around raw UIA elements."""

    ROLE_MAP = {
        "Edit": "Input field",
        "Button": "Button",
        "Hyperlink": "Link",
        "MenuItem": "Menu item",
        "Document": "Document",
        "Pane": "Panel",
        "Group": "Group",
        "Custom": "Element",
        "CheckBox": "Checkbox",
        "RadioButton": "Radio button",
        "ComboBox": "Dropdown",
        "ListItem": "List item",
        "TabItem": "Tab",
        "Text": "Text",
    }

    def __init__(self, element: Any, index: int):
        self.element = element
        self.index = index
        self.name = self._safe_name()
        self.role = self._safe_role()
        self.control_type = self.role
        self.automation_id = self._safe_automation_id()
        self.bounding_rect = self._safe_bounding_rect()
        self.region = self._infer_region()

    def _safe_name(self) -> str:
        try:
            return (
                self.element.element_info.name
                or self.element.window_text()
                or self.element.element_info.class_name
                or "Unnamed"
            )
        except Exception:
            pass
        try:
            value = getattr(self.element, "CurrentName", None)
            if value:
                return str(value)
        except Exception:
            pass
        return "Unknown"

    def _safe_role(self) -> str:
        try:
            return self.element.friendly_class_name()
        except Exception:
            pass
        try:
            value = getattr(self.element, "CurrentLocalizedControlType", None)
            if value:
                return str(value).title()
        except Exception:
            pass
        return "Element"

    def _infer_region(self) -> Optional[str]:
        lower_name = (self.name or "").lower()
        if any(token in lower_name for token in {"chat", "conversation", "history"}):
            return "sidebar"
        if any(token in lower_name for token in {"message", "reply", "thread"}):
            return "main"
        if self.is_input():
            return "input"
        return None

    def _safe_automation_id(self) -> str:
        try:
            return self.element.element_info.automation_id or ""
        except Exception:
            pass
        try:
            value = getattr(self.element, "CurrentAutomationId", None)
            if value:
                return str(value)
        except Exception:
            pass
        return ""

    def _safe_bounding_rect(self):
        try:
            rect = self.element.rectangle()
            return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass
        try:
            rect = getattr(self.element, "CurrentBoundingRectangle", None)
            if rect is not None:
                return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass
        return None

    def speakable(self) -> str:
        role = self.ROLE_MAP.get(self.role, self.role)
        if self.name:
            return f"{role}: {self.name}"
        return role

    def set_focus(self) -> None:
        try:
            dispatcher.call(self.element.set_focus)
        except Exception:
            pass

    def click(self) -> None:
        try:
            dispatcher.call(self.element.invoke)
            return
        except Exception:
            pass
        try:
            dispatcher.call(self.element.click_input)
        except Exception:
            pass

    def is_button(self) -> bool:
        return self.role == "Button"

    def is_input(self) -> bool:
        return self.role in {"Edit", "TextBox"}

    def is_link(self) -> bool:
        return self.role == "Hyperlink"


class AccessibilityNavigator:
    """
    Production accessibility navigation facade backed by the
    NavigationOrchestrator.
    """

    SAFE_ROLES = {
        "Button",
        "Edit",
        "MenuItem",
        "CheckBox",
        "ComboBox",
        "Document",
        "ListItem",
        "TreeItem",
        "TabItem",
    }
    INTERACTIVE_SCAN_ROLES = {
        "Button",
        "MenuItem",
        "Edit",
        "CheckBox",
        "ComboBox",
        "ListItem",
        "TabItem",
    }
    WINDOW_CONTROL_NAMES = {"minimize", "maximize", "restore", "close"}
    MAX_SCAN_DEPTH = 3
    MAX_SCAN_NODES = 120
    MAX_CHILDREN = 30
    SCAN_TIMEOUT = 1.2
    READ_SCREEN_TIMEOUT = 2.0
    SCREEN_SUMMARY_CACHE_SECONDS = 2.5

    def __init__(self, uia_client=None, vision_executor=None):
        self.logger = get_logger("accessibility.navigator")
        self.uia_client = uia_client
        self.vision_executor = vision_executor
        self.runtime = None
        self.state = NavigationState()
        self.tree = AccessibilityTree()
        self.tree_builder = AccessibilityTreeBuilder()
        self.output_filter = OutputFilter()
        self.nvda_reader = NVDAReader()
        self.semantic_analyzer = SemanticScreenAnalyzer()
        self.last_announced: Optional[str] = None
        self.last_accessibility_metadata = {}
        self.last_screen_summary: Optional[str] = None
        self.last_screen_summary_at = 0.0
        self._cached_hwnd = None
        self._cached_window = None
        self._cached_element_scan = []
        self._cached_element_scan_at = 0.0
        self.snapshot_cache = NavigationSnapshotCache(ttl_seconds=self.SCREEN_SUMMARY_CACHE_SECONDS)
        self.orchestrator = NavigationOrchestrator(
            state=self.state,
            cache=self.snapshot_cache,
            window_provider=self._window_name,
            focus_provider=self._get_focused,
            scanner=self._collect_elements,
            announcer=self._announce_text,
            keyboard_next=self._keyboard_move,
            keyboard_activate=self._keyboard_activate,
            focus_setter=self._focus_element,
        )

    def _nav_trace(self, message: str) -> None:
        print(f"[NAV TRACE {time.time():.3f}] {message}")

    def _uia_trace(self, message: str) -> None:
        print(f"[UIA TRACE {time.time():.3f}] {message}")

    def _window_name(self) -> str:
        try:
            window = self._get_active_window()
            if window is not None:
                return window.window_text()
        except Exception:
            pass
        return self.state.window or "Unknown window"

    def _get_active_window(self):
        if self._cached_window is not None:
            return self._cached_window
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(dispatcher.call, self._get_active_window_internal)
            window = future.result(timeout=0.6)
            if window is not None:
                self._cached_window = window
            return window
        except TimeoutError:
            return self._cached_window
        except Exception:
            return self._cached_window
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _window_name_internal(self) -> str:
        return self._get_active_window_internal().window_text()

    def _get_active_window_internal(self):
        self._nav_trace("_get_active_window start")
        if win32gui is None or Application is None:
            raise RuntimeError("Windows UI automation is unavailable.")
        hwnd = win32gui.GetForegroundWindow()
        self._nav_trace(f"_get_active_window hwnd={hwnd}")
        if self._cached_hwnd != hwnd:
            self._cached_hwnd = hwnd
            self._cached_window = None
            self._cached_element_scan = []
            self._cached_element_scan_at = 0.0
        if self._cached_window is not None:
            return self._cached_window
        app = Application(backend="uia").connect(handle=hwnd)
        self._nav_trace("_get_active_window connected")
        self._cached_window = app.window(handle=hwnd)
        return self._cached_window

    def _get_focused(self):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._get_focused_internal)
            return future.result(timeout=0.4)
        except TimeoutError:
            return self.state.current()
        except Exception:
            return self.state.current()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _get_focused_internal(self):
        self._nav_trace("_get_focused start")
        if Desktop is None:
            return None
        try:
            focused = Desktop(backend="uia").get_focus()
        except Exception:
            return None
        self._nav_trace("_get_focused resolved")
        return UIElementWrapper(focused, -1)

    def _announce_text(self, text: str) -> Optional[str]:
        filtered = self.output_filter.clean(text)
        if filtered:
            self.last_announced = filtered
        return filtered

    def _clean_speech(self, text: Optional[str], fallback: str = "") -> str:
        cleaned = " ".join((text or "").split()).strip()
        return cleaned or fallback

    def _current_window_name(self) -> str:
        return self.state.window or self._window_name() or "current window"

    def _cached_snapshot(self):
        return self.snapshot_cache.get(self._current_window_name())

    def _role_label(self, role: str) -> str:
        if not role:
            return "Element"
        return UIElementWrapper.ROLE_MAP.get(role, role)

    def _fallback_screen_message(
        self,
        *,
        window_name: Optional[str] = None,
        focused: Optional[Any] = None,
        elements: Optional[List[Any]] = None,
    ) -> str:
        window_name = window_name or self._current_window_name()
        focused = focused or self.state.current() or self._get_focused()
        if focused is not None:
            return f"You're currently on {window_name}. {self._clean_speech(self._describe_element(focused))}"

        snapshot = self._cached_snapshot()
        source_elements = elements or (snapshot.elements if snapshot else None) or self.state.elements
        described = self._describe_elements(source_elements, limit=3)
        if described:
            return f"You're currently on {window_name}. I can see {described}."

        if self.last_screen_summary and (time.time() - self.last_screen_summary_at) <= self.SCREEN_SUMMARY_CACHE_SECONDS:
            return self.last_screen_summary

        return f"You're currently on {window_name}."

    def _describe_element(self, element: Any) -> str:
        spoken = self._clean_speech(self.orchestrator._describe(element))
        return spoken or "current element"

    def _describe_elements(self, elements: Optional[List[Any]], *, limit: int = 3) -> str:
        if not elements:
            return ""
        parts = []
        for element in elements[:limit]:
            phrase = self._clean_speech(self._describe_element(element))
            if phrase:
                parts.append(phrase)
        return ", ".join(parts)

    def _store_screen_summary(self, speech: str) -> None:
        cleaned = self._clean_speech(speech)
        if cleaned:
            self.last_screen_summary = cleaned
            self.last_screen_summary_at = time.time()

    def _fast_focus_summary(self) -> Optional[str]:
        try:
            focused = self._get_focused()
            window = self._get_active_window()

            if focused is None or window is None:
                return None

            title = self._clean_speech(window.window_text(), "current window")
            role = self._clean_speech(
                getattr(focused, "control_type", None) or getattr(focused, "role", None) or "Element"
            )
            name = self._clean_speech(getattr(focused, "name", None), "Unnamed")

            summary = f"You're currently in {title}. Focused element: {self._role_label(role)} {name}"
            return self._clean_speech(summary)
        except Exception:
            return None

    def _context_summary(self) -> Optional[str]:
        return dispatcher.call(self._context_summary_internal)

    def _context_summary_internal(self) -> Optional[str]:
        try:
            window = self._get_active_window_internal()
        except Exception:
            return None

        title = self._clean_speech(window.window_text(), "current window")

        try:
            children = window.children()[: self.MAX_CHILDREN]
        except Exception:
            children = []

        has_menu = False
        has_toolbar = False
        has_editor = False
        has_sidebar = False

        for child in children:
            try:
                role = self._clean_speech(child.friendly_class_name())
                name = self._clean_speech(
                    child.element_info.name or child.window_text() or child.element_info.class_name
                ).lower()
            except Exception:
                continue

            if role in {"MenuBar", "MenuItem"} or "menu" in name:
                has_menu = True
            if role == "ToolBar" or "toolbar" in name:
                has_toolbar = True
            if role in {"Document", "Edit"} or any(token in name for token in {"editor", "document", "text editor"}):
                has_editor = True
            if role in {"Tree", "TreeItem"} or any(token in name for token in {"explorer", "sidebar", "outline"}):
                has_sidebar = True

        parts = [title]
        if has_menu:
            parts.append("Menu bar available.")
        if has_toolbar:
            parts.append("Toolbar visible.")
        if has_sidebar:
            parts.append("Explorer sidebar visible.")
        if has_editor:
            parts.append("Editor open.")

        if len(parts) == 1:
            return f"You're currently in {title}."

        return " ".join(parts)

    def _focus_element(self, element: Any) -> bool:
        if element is None:
            return False
        setter = getattr(element, "set_focus", None)
        if not callable(setter):
            return False
        try:
            setter()
            self.state.set_focused(element)
            return True
        except Exception:
            return False

    def _keyboard_move(self, reverse: bool = False):
        if send_keys is None:
            return None
        try:
            send_keys("+{TAB}" if reverse else "{TAB}")
            time.sleep(0.08)
            return self._get_focused()
        except Exception:
            return None

    def _keyboard_activate(self) -> bool:
        if send_keys is None:
            return False
        try:
            send_keys("{ENTER}")
            return True
        except Exception:
            return False

    def describe_context(self):
        try:
            window = self._get_active_window()
            focused = self._get_focused()

            if not window:
                return "I cannot determine the current screen."

            title = window.window_text()

            return self.semantic_analyzer.analyze(title, focused)
        except Exception:
            return "I cannot determine the current screen."

    def scan_interactive_elements(self, force: bool = False):
        try:
            window = self._get_active_window()
        except Exception:
            return []

        if not window:
            return []

        now = time.time()
        if (
            not force
            and self._cached_element_scan
            and (now - self._cached_element_scan_at) <= 1.0
        ):
            return list(self._cached_element_scan)

        elements = []
        seen = set()

        def walk(node, depth):
            if depth > 6 or len(elements) >= 250:
                return

            try:
                role = node.friendly_class_name()
                name = node.element_info.name or node.window_text() or ""
                automation_id = getattr(node.element_info, "automation_id", "") or ""
                normalized_name = re.sub(r"[^\w\s]", "", str(name).lower()).strip()
                key = f"{role}:{normalized_name}:{automation_id}"

                if (
                    role in self.INTERACTIVE_SCAN_ROLES
                    and normalized_name
                    and normalized_name not in self.WINDOW_CONTROL_NAMES
                    and key not in seen
                ):
                    seen.add(key)
                    elements.append(UIElementWrapper(node, len(elements)))
            except Exception:
                pass

            try:
                for child in node.children():
                    walk(child, depth + 1)
            except Exception:
                pass

        started = time.perf_counter()
        walk(window, 0)
        self._cached_element_scan = elements
        self._cached_element_scan_at = now
        self.state.load(window.window_text(), elements)
        self.tree.load(window.window_text(), elements)
        self.logger.info(
            "TREE_REBUILT",
            window=window.window_text(),
            element_count=len(elements),
            depth=6,
        )
        self.logger.debug(
            "ui_scan_recursive",
            depth=6,
            element_count=len(elements),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return list(elements)

    def get_accessibility_tree(self, force: bool = False):
        elements = self.scan_interactive_elements(force=force)
        self.tree.load(self.state.window or "Unknown window", elements)
        return self.tree

    def _collect_elements(self) -> Tuple[str, List[UIElementWrapper]]:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(dispatcher.call, self._collect_elements_internal)
            return future.result(timeout=1.2)
        except TimeoutError:
            snapshot = self._cached_snapshot()
            if snapshot is not None:
                return snapshot.window_name, list(snapshot.elements or [])
            return self.state.window or "Unknown window", list(self.state.elements or [])
        except Exception:
            snapshot = self._cached_snapshot()
            if snapshot is not None:
                return snapshot.window_name, list(snapshot.elements or [])
            return self.state.window or "Unknown window", list(self.state.elements or [])
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _collect_elements_internal(self) -> Tuple[str, List[UIElementWrapper]]:
        self._nav_trace("starting UI scan")
        try:
            window = self._get_active_window_internal()
        except Exception:
            return self._collect_elements_from_uia_client()

        self._uia_trace("UI scan started")
        elements: List[UIElementWrapper] = []
        seen = set()
        queue = [(window, 0)]
        visited = 0
        start_time = time.perf_counter()

        while queue and visited < self.MAX_SCAN_NODES:
            if (time.perf_counter() - start_time) > self.SCAN_TIMEOUT:
                break

            current, depth = queue.pop(0)
            visited += 1
            self._uia_trace(f"scanning node {visited}")

            try:
                role = current.friendly_class_name()
            except Exception:
                role = "Unknown"

            try:
                name = current.element_info.name or current.window_text() or ""
            except Exception:
                name = ""

            try:
                self._uia_trace(f"element role={role} name={name}")
                lower_name = name.lower()

                if "toggle screen reader accessibility mode" in lower_name:
                    continue
                if "run the command" in lower_name:
                    continue

                key = f"{role}:{name}"
                if (
                    role in self.SAFE_ROLES
                    and name
                    and lower_name not in self.WINDOW_CONTROL_NAMES
                    and len(name) < 160
                    and key not in seen
                ):
                    seen.add(key)
                    elements.append(UIElementWrapper(current, len(elements)))
                    self._uia_trace(f"accepted element #{len(elements)}")
                    if len(elements) >= 10:
                        break
            except Exception:
                pass

            try:
                self._uia_trace("retrieving children")
                if depth >= self.MAX_SCAN_DEPTH:
                    children = []
                else:
                    children = current.children()[: self.MAX_CHILDREN]
                self._uia_trace(f"children count={len(children)}")
                for child in children:
                    queue.append((child, depth + 1))
            except Exception:
                pass

        self._uia_trace("UI scan finished")
        self._nav_trace(f"elements found: {len(elements)}")
        return window.window_text(), elements

    def _collect_elements_from_uia_client(self) -> Tuple[str, List[UIElement]]:
        if not self.uia_client:
            return self.state.window or "Unknown window", []

        try:
            payload = self.uia_client.read_screen()
        except Exception:
            return self.state.window or "Unknown window", []

        if not isinstance(payload, dict) or payload.get("status") != "success":
            return self.state.window or "Unknown window", []

        elements = []
        for index, item in enumerate(payload.get("elements", [])):
            if not isinstance(item, dict):
                continue
            elements.append(
                UIElement(
                    name=item.get("name"),
                    control_type=item.get("type"),
                    index=item.get("index", index),
                    region=item.get("region"),
                )
            )

        return payload.get("window", self.state.window or "Unknown window"), elements

    def _result_message(self, result) -> str:
        if result.success:
            return result.spoken_message
        return result.spoken_message or "Navigation failed."

    def _set_reader_metadata(self, metadata: Optional[dict]) -> None:
        self.last_accessibility_metadata = dict(metadata or {})

    def consume_metadata(self) -> dict:
        metadata = dict(self.last_accessibility_metadata or {})
        self.last_accessibility_metadata = {}
        return metadata

    def _window_from_result(self, result) -> str:
        if getattr(result, "snapshot", None) and getattr(result.snapshot, "window_name", None):
            return result.snapshot.window_name
        return self._window_name()

    def _elements_from_result(self, result):
        if getattr(result, "elements", None):
            return result.elements
        if getattr(result, "snapshot", None) and getattr(result.snapshot, "elements", None):
            return result.snapshot.elements
        return []

    def _focused_from_result(self, result):
        if getattr(result, "element", None) is not None:
            return result.element
        if getattr(result, "snapshot", None):
            return getattr(result.snapshot, "focused_element", None)
        return None

    def _nvda_focus_message(self, result, *, fallback: str, context_label: Optional[str] = None) -> str:
        reader_result = self.nvda_reader.read_focused_element(
            window_name=self._window_from_result(result),
            focused_element=self._focused_from_result(result),
            fallback_text=fallback,
            context_label=context_label,
        )
        self._set_reader_metadata(reader_result.metadata)
        return reader_result.spoken_message

    def refresh_elements(self):
        snapshot = self.orchestrator.refresh()
        return snapshot.elements

    def _fallback_focus(self) -> str:
        try:
            window = self._get_active_window()
            focused = self._get_focused() or self.state.current()
            title = self._clean_speech(window.window_text(), "current window") if window else "current window"
            if focused is not None:
                role = self._clean_speech(
                    getattr(focused, "control_type", None) or getattr(focused, "role", None) or "Element"
                )
                name = self._clean_speech(getattr(focused, "name", None), "Unnamed")
                return f"You are in {title}. Focused element: {self._role_label(role)} {name}."
            return f"You are in {title}."
        except Exception:
            return "You are in the current window."

    def _read_screen_internal(self, stop_event: Optional[threading.Event] = None) -> Tuple[List[Any], str]:
        self.logger.debug("read_screen_start")
        if stop_event and stop_event.is_set():
            return [], self._fallback_screen_message()
        self._nav_trace("_read_screen_internal start")
        window_name = self._current_window_name()
        focused = self._get_focused() or self.state.current()
        cached_snapshot = self._cached_snapshot()

        if focused is not None:
            focus_message = f"You're currently on {window_name}. {self._describe_element(focused)}"
            if cached_snapshot and cached_snapshot.elements:
                described = self._describe_elements(cached_snapshot.elements, limit=3)
                if described:
                    focus_message = f"{focus_message}. I can also see {described}."
            self._store_screen_summary(focus_message)
            self._set_reader_metadata({"used_nvda_speech": False, "suppress_tts": False, "source": "focus_fast_path"})
            return list(cached_snapshot.elements) if cached_snapshot and cached_snapshot.elements else [], focus_message

        if cached_snapshot and cached_snapshot.elements:
            cached_message = f"You're currently on {cached_snapshot.window_name}. I can see {self._describe_elements(cached_snapshot.elements, limit=3)}."
            self._store_screen_summary(cached_message)
            self._set_reader_metadata({"used_nvda_speech": False, "suppress_tts": False, "source": "cache_fast_path"})
            return list(cached_snapshot.elements), cached_message

        if stop_event and stop_event.is_set():
            return [], self._fallback_screen_message(window_name=window_name, focused=focused)

        self._nav_trace("starting UI scan")
        result = self.orchestrator.execute(NavigationCommand(action="read_screen"))
        if stop_event and stop_event.is_set():
            return [], self._fallback_screen_message(
                window_name=self._window_from_result(result),
                focused=self._focused_from_result(result),
                elements=self._elements_from_result(result),
            )
        self._nav_trace(f"elements found: {len(self._elements_from_result(result))}")
        fallback = self._fallback_screen_message(
            window_name=self._window_from_result(result),
            focused=self._focused_from_result(result),
            elements=self._elements_from_result(result),
        )
        reader_result = self.nvda_reader.read_screen(
            window_name=self._window_from_result(result),
            elements=self._elements_from_result(result),
            focused_element=self._focused_from_result(result),
            fallback_text=fallback,
        )
        self._set_reader_metadata(reader_result.metadata)
        speech = self._clean_speech(reader_result.spoken_message, fallback)
        if speech == "No readable content found.":
            speech = fallback
        self._store_screen_summary(speech)
        self._nav_trace("building screen summary")
        self.logger.debug(
            "read_screen_end",
            source=reader_result.source,
            used_cache=reader_result.used_cache,
            element_count=len(self._elements_from_result(result)),
            speech_length=len(speech),
        )
        return self._elements_from_result(result), speech

    def read_screen_details(self) -> Tuple[List[Any], str]:
        self._nav_trace("read_screen_details start")
        fast = self._fast_focus_summary()
        if fast:
            self._store_screen_summary(fast)
            self._set_reader_metadata({"used_nvda_speech": False, "suppress_tts": False, "source": "focus_fast_path"})
            return [], fast

        context = self._context_summary()
        if context:
            self._store_screen_summary(context)
            self._set_reader_metadata({"used_nvda_speech": False, "suppress_tts": False, "source": "context_summary"})
            return [], context

        stop_event = threading.Event()
        focus_listener = getattr(self.runtime, "focus_listener", None) if self.runtime else None

        if focus_listener:
            try:
                focus_listener.pause()
            except Exception:
                pass

        self._nav_trace("spawning read_screen worker")
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="AccessibilityReadScreen")
        try:
            self._nav_trace("read_screen worker started")
            future = executor.submit(dispatcher.call, self._read_screen_internal, stop_event=stop_event)

            try:
                payload = future.result(timeout=self.READ_SCREEN_TIMEOUT)
                self._nav_trace("worker finished")
                return payload
            except TimeoutError:
                stop_event.set()
                future.cancel()
                self._nav_trace("read_screen worker timeout")
                self.logger.debug(
                    "read_screen_timeout",
                    timeout_seconds=self.READ_SCREEN_TIMEOUT,
                )
                self._set_reader_metadata({})
                return [], f"I couldn't fully scan the screen, but I can tell you the current window. {self._fallback_focus()}"
            except Exception as exc:
                self.logger.error("read_screen_failed", exception=exc)
                self._set_reader_metadata({})
                return [], self._fallback_screen_message()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            if focus_listener:
                try:
                    focus_listener.resume()
                except Exception:
                    pass

    def read_screen(self) -> str:
        _, speech = self.read_screen_details()
        return self._clean_speech(speech, self._fallback_screen_message())

    def next_item(self):
        result = self.orchestrator.execute(NavigationCommand(action="next"))
        fallback = self._result_message(result)
        if not result.success:
            self._set_reader_metadata({})
            return fallback
        return self._nvda_focus_message(result, fallback=fallback, context_label="Next item")

    def previous_item(self):
        result = self.orchestrator.execute(NavigationCommand(action="previous"))
        fallback = self._result_message(result)
        if not result.success:
            self._set_reader_metadata({})
            return fallback
        return self._nvda_focus_message(result, fallback=fallback, context_label="Previous item")

    def activate(self):
        result = self.orchestrator.execute(NavigationCommand(action="activate"))
        self._set_reader_metadata({})
        return self._result_message(result)

    def read_current(self):
        result = self.orchestrator.execute(NavigationCommand(action="read_current"))
        fallback = self._result_message(result)
        return self._nvda_focus_message(result, fallback=fallback)

    def _next_semantic(self, semantic_type: str, empty_message: str) -> str:
        result = self.orchestrator.execute(
            NavigationCommand(action="semantic_next", semantic_type=semantic_type)
        )
        if not result.success:
            self._set_reader_metadata({})
            return empty_message
        fallback = self._result_message(result)
        return self._nvda_focus_message(result, fallback=fallback, context_label=f"Next {semantic_type}")

    def next_button(self):
        return self._next_semantic("button", "No buttons found.")

    def next_input(self):
        return self._next_semantic("input", "No input fields found.")

    def next_link(self):
        return self._next_semantic("link", "No links found.")

    def next_tab(self):
        return self._next_semantic("tab", "No tabs found.")

    def next_menu(self):
        return self._next_semantic("menu", "No menu items found.")

    def next_chat(self):
        return self._next_semantic("chat", "No chat items found.")

    def next_message(self):
        return self._next_semantic("message", "No messages found.")

    def focus_input(self):
        result = self.orchestrator.execute(NavigationCommand(action="focus_input"))
        if not result.success:
            self._set_reader_metadata({})
            return "No input fields found."
        fallback = self._result_message(result)
        return self._nvda_focus_message(result, fallback=fallback, context_label="Focused input")

    def read_content(self):
        return self.read_screen()

    def read_conversation(self):
        elements = [
            self._announce_text(item.speakable())
            for item in self.state.elements
            if getattr(item, "region", None) in {"sidebar", "main"}
        ]
        lines = [line for line in elements if line]
        if not lines:
            return "No conversation content detected."
        return "\n".join(lines[:12])
