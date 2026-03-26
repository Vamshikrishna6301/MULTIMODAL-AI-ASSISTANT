class AccessibilityTree:
    """
    Cached accessibility tree used for navigation.
    Prevents rescanning the UI every command.
    """

    def __init__(self):

        self.window = None
        self.elements = []
        self.index = 0

    # =====================================================
    # LOAD NEW TREE
    # =====================================================

    def load(self, window, elements):

        self.window = window
        self.elements = elements or []
        self.index = 0

    # =====================================================
    # CURRENT ELEMENT
    # =====================================================

    def current(self):

        if not self.elements:
            return None

        return self.elements[self.index]

    # =====================================================
    # NEXT ELEMENT
    # =====================================================

    def next(self):

        if not self.elements:
            return None

        self.index = min(self.index + 1, len(self.elements) - 1)

        return self.current()

    # =====================================================
    # PREVIOUS ELEMENT
    # =====================================================

    def previous(self):

        if not self.elements:
            return None

        self.index = max(self.index - 1, 0)

        return self.current()