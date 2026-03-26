from execution.accessibility.accessibility_tree import AccessibilityTree


class AccessibilityNode:

    def __init__(self, role, name, element=None):

        self.role = role
        self.name = name
        self.element = element
        self.children = []

    def add_child(self, node):

        self.children.append(node)


class AccessibilityTreeBuilder:
    """
    Production Accessibility Tree Builder

    Improvements
    ------------
    - Prevents massive UIA scans
    - Limits node counts
    - Filters noisy elements
    - Builds semantic regions
    """

    MAX_ELEMENTS = 250
    MAX_CHILDREN = 40
    MAX_DEPTH = 6

    VALID_ROLES = {
        "button",
        "menuitem",
        "tabitem",
        "edit",
        "checkbox",
        "combobox",
        "listitem",
    }

    # =====================================================

    def build(self, window, elements):

        root = AccessibilityNode("window", window)
        tree = AccessibilityTree()
        flattened = []

        sidebar = AccessibilityNode("sidebar", "Sidebar")
        conversation = AccessibilityNode("conversation", "Conversation")
        input_area = AccessibilityNode("input", "Input")

        def add_element(el):
            if len(flattened) >= self.MAX_ELEMENTS:
                return

            name = getattr(el, "name", None)
            if not name:
                return

            role = getattr(el, "control_type", "").lower()
            if role not in self.VALID_ROLES:
                return

            flattened.append(el)
            region = getattr(el, "region", None)

            if region == "sidebar":
                sidebar.add_child(
                    AccessibilityNode(
                        role="chat",
                        name=el.name,
                        element=el
                    )
                )
            elif region == "main":
                conversation.add_child(
                    AccessibilityNode(
                        role="message",
                        name=el.name,
                        element=el
                    )
                )
            else:
                node_role = "input_field" if getattr(el, "is_input", lambda: False)() else role
                input_area.add_child(
                    AccessibilityNode(
                        role=node_role,
                        name=el.name,
                        element=el
                    )
                )

        if elements and not hasattr(elements, "children"):
            for el in elements:
                add_element(el)
        else:
            def scan(element, depth):
                if depth > self.MAX_DEPTH or len(flattened) >= self.MAX_ELEMENTS or element is None:
                    return
                try:
                    children = element.children()[: self.MAX_CHILDREN]
                except Exception:
                    children = []
                for child in children:
                    add_element(child)
                    scan(child, depth + 1)

            scan(elements, 0)

        # Attach sections to root

        if sidebar.children:
            root.add_child(sidebar)

        if conversation.children:
            root.add_child(conversation)

        if input_area.children:
            root.add_child(input_area)

        tree.load(window, flattened)
        root.tree = tree
        return root
