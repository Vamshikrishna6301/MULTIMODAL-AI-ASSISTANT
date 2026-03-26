import threading
from typing import List, Optional


class NavigationState:
    """
    Production navigation state manager.

    Responsibilities:
    - Maintain UI element cache
    - Track navigation cursor
    - Track real-time focused element
    - Provide safe navigation helpers

    Designed for:
    - UIA focus event integration
    - fast screen reader navigation
    """

    def __init__(self):

        # thread safety
        self._lock = threading.RLock()

        # current active window title
        self.window: Optional[str] = None

        # cached UI elements (UIElementWrapper list)
        self.elements: List = []

        # navigation cursor
        self.index: int = -1

        # real focused element (from UIA events)
        self.focused_element = None

    # =====================================================
    # LOAD ELEMENTS
    # =====================================================

    def load(self, window: str, elements: List):

        with self._lock:

            # if window changed reset state
            if window != self.window:
                self.focused_element = None

            self.window = window
            self.elements = elements or []

            if self.elements:
                self.index = 0
            else:
                self.index = -1

    # =====================================================
    # FOCUS TRACKING
    # =====================================================

    def set_focused(self, element):
        """
        Called by UIA focus event listener.
        """

        if element is None:
            return

        with self._lock:
            self.focused_element = element

    # =====================================================
    # CURRENT ELEMENT
    # =====================================================

    def current(self):

        with self._lock:

            # prefer real focus
            if self.focused_element:
                return self.focused_element

            if not self.elements:
                return None

            if self.index < 0 or self.index >= len(self.elements):
                return None

            return self.elements[self.index]

    # =====================================================
    # NEXT ELEMENT
    # =====================================================

    def next(self):

        with self._lock:

            if not self.elements:
                return None

            self.index += 1

            if self.index >= len(self.elements):
                self.index = 0

            return self.elements[self.index]

    # =====================================================
    # PREVIOUS ELEMENT
    # =====================================================

    def previous(self):

        with self._lock:

            if not self.elements:
                return None

            self.index -= 1

            if self.index < 0:
                self.index = len(self.elements) - 1

            return self.elements[self.index]

    # =====================================================
    # SEMANTIC SEARCH
    # =====================================================

    def find_next(self, predicate):

        """
        Find next element matching condition.
        Used for:
        - next button
        - next link
        - next input
        """

        with self._lock:

            if not self.elements:
                return None

            start = self.index + 1

            for i in range(start, len(self.elements)):

                el = self.elements[i]

                try:
                    if predicate(el):
                        self.index = i
                        return el
                except Exception:
                    continue

            return None

    # =====================================================
    # RESET STATE
    # =====================================================

    def reset(self):

        with self._lock:

            self.window = None
            self.elements = []
            self.index = -1
            self.focused_element = None

    # =====================================================
    # DEBUG INFO
    # =====================================================

    def debug_info(self):

        with self._lock:

            return {
                "window": self.window,
                "elements": len(self.elements),
                "index": self.index,
                "focused": bool(self.focused_element),
            }