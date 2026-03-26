from execution.accessibility.ui_element import UIElement
from execution.accessibility.browser_dom_reader import BrowserDOMReader
from execution.accessibility.browser_detector import is_browser


class PerceptionEngine:
    """
    Unified perception layer for desktop and browser apps.
    """

    MAX_ELEMENTS = 15

    INTERACTIVE_ROLES = {
        "button",
        "hyperlink",
        "edit",
        "textarea",
        "menuitem",
        "tabitem",
        "combobox",
        "checkbox",
        "radiobutton",
        "listitem",
        "treeitem"
    }

    IGNORED_NAMES = {
        "Minimize",
        "Restore",
        "Close"
    }

    IGNORED_ROLES = {
        "Pane",
        "Group",
        "Container",
        "Text",
        "Document",
        "Separator",
        "TitleBar"
    }

    def __init__(self, uia_client, vision_executor):
        self.uia = uia_client
        self.vision = vision_executor
        self.dom_reader = BrowserDOMReader()

    # -----------------------------------------------------

    def perceive(self):

        # Browser perception
        if is_browser():

            dom = self.dom_reader.read_page()

            if dom:
                elements = []

                for e in dom:

                    elements.append(
                        UIElement(
                            name=e.get("name"),
                            control_type=e.get("role"),
                            selector=e.get("selector"),
                            region=e.get("region")
                        )
                    )

                elements = self._rank(elements)

                return "Browser Page", elements[:self.MAX_ELEMENTS]

        # Desktop UI Automation fallback
        result = self.uia.read_screen()

        if not isinstance(result, dict):
            return None, []

        if result.get("status") != "success":
            return None, []

        window = result.get("window", "Unknown window")

        raw = result.get("elements", [])

        elements = []

        for el in raw:

            name = el.get("name")
            role = el.get("role")

            if not name:
                continue

            if name in self.IGNORED_NAMES:
                continue

            if role in self.IGNORED_ROLES:
                continue

            elements.append(
                UIElement(
                    name=name,
                    control_type=role,
                    index=el.get("index"),
                    bbox=el.get("bbox")
                )
            )

        elements = self._rank(elements)

        return window, elements[:self.MAX_ELEMENTS]

    # -----------------------------------------------------

    def _priority(self, e):

        role = (e.control_type or "").lower()
        visible = getattr(e, "visible", True)

        if visible and role == "menuitem":
            return 0

        if visible and role == "button":
            return 1

        if visible and role in {"edit", "textarea", "combobox"}:
            return 2

        if role in self.INTERACTIVE_ROLES:
            return 3

        if role == "tabitem":
            return 4

        if role == "menuitem":
            return 5

        return 6

    # -----------------------------------------------------

    def _rank(self, elements):

        def key(e):

            top = 9999
            left = 9999

            if e.bbox:
                left = e.bbox[0]
                top = e.bbox[1]

            return (
                self._priority(e),
                top,
                left
            )

        return sorted(elements, key=key)
