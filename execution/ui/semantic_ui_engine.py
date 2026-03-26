"""
Semantic UI Engine
Stable Single-Threaded UIA Version

- No threading
- No locks
- Depth limited traversal
- Timeout protected
- Safe click validation
"""

import time
from typing import List, Dict
from pywinauto import Desktop


class SemanticUIEngine:

    MAX_DEPTH = 4
    MAX_ELEMENTS = 50
    TIMEOUT_SECONDS = 3

    INTERACTIVE_TYPES = {
        "Button",
        "Hyperlink",
        "Edit",
        "MenuItem",
        "ListItem",
        "CheckBox",
        "RadioButton",
        "ComboBox",
        "TabItem"
    }

    def __init__(self):
        self.desktop = Desktop(backend="uia")
        self.current_elements: List[Dict] = []
        self.active_window_title = None

    # =====================================================a
    # ACTIVE WINDOW
    # =====================================================

    def _get_active_window(self):
        try:
            window = self.desktop.window(active_only=True)
            window.set_focus()
            return window
        except Exception:
            return None
    #=========================
    # RECURSIVE TRAVERSAL
    # =====================================================

    def _traverse(self, element, depth, start_time):

        if depth > self.MAX_DEPTH:
            return

        if len(self.current_elements) >= self.MAX_ELEMENTS:
            return

        if time.time() - start_time > self.TIMEOUT_SECONDS:
            return

        try:
            children = element.children()
        except Exception:
            return

        for child in children:

            if len(self.current_elements) >= self.MAX_ELEMENTS:
                return

            if time.time() - start_time > self.TIMEOUT_SECONDS:
                return

            try:
                if not child.is_visible() or not child.is_enabled():
                    continue

                name = child.window_text()
                control_type = child.element_info.control_type
                print("DEBUG CHILD:", control_type, "|", name)
                if name and control_type in self.INTERACTIVE_TYPES:
                    self.current_elements.append({
                        "index": len(self.current_elements) + 1,
                        "name": name.strip(),
                        "type": control_type,
                        "element": child
                    })

                # Traverse deeper
                self._traverse(child, depth + 1, start_time)

            except Exception:
                continue

    # =====================================================
    # EXTRACTION
    # =====================================================

    def extract_interactive_elements(self) -> List[Dict]:

        self.current_elements = []

        window = self._get_active_window()

        if window is None:
            return []

        try:
            self.active_window_title = window.window_text()
            print("DEBUG ACTIVE WINDOW:", self.active_window_title)
        except Exception:
            return []

        start_time = time.time()

        self._traverse(window, depth=0, start_time=start_time)

        return self.current_elements

    # =====================================================
    # READ SCREEN
    # =====================================================

    def read_screen(self) -> str:

        elements = self.extract_interactive_elements()

        if not elements:
            return "__NO_UIA_ELEMENTS__"

        window_name = self.active_window_title or "current window"

        summary_lines = []

        for el in elements[:12]:
            summary_lines.append(
                f"{el['index']}. {el['type']} {el['name']}"
            )

        speech = (
            f"You are in {window_name}. "
            f"I found {len(elements)} interactive elements. "
            + ", ".join(summary_lines)
            + ". Say click number followed by the number."
        )

        return speech

    # =====================================================
    # CLICK
    # =====================================================

    def click_element_by_index(self, index: int) -> str:

        if not self.current_elements:
            return "No elements available. Say what is on my screen first."

        current_window = self._get_active_window()

        if not current_window:
            return "The screen changed. Please try again."

        if current_window.window_text() != self.active_window_title:
            return "The screen has changed. Please ask what is on my screen again."

        for element in self.current_elements:
            if element["index"] == index:
                try:
                    ui_element = element["element"]

                    if not ui_element.is_visible() or not ui_element.is_enabled():
                        return "That item is no longer available."

                    ui_element.invoke()
                    return f"Clicked {element['name']}."

                except Exception:
                    return "I could not click that item safely."

        return "Invalid selection number."