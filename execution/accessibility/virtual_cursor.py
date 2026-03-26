class VirtualCursor:
    """
    Virtual accessibility cursor.

    Flattens the accessibility tree into a linear buffer
    similar to NVDA/VoiceOver virtual buffers.
    """

    def __init__(self):
        self.nodes = []
        self.index = -1

    # -------------------------------------------------

    def build(self, tree):

        self.nodes = []
        self.index = -1

        self._walk(tree)

        if self.nodes:
            self.index = 0

    # -------------------------------------------------

    def _walk(self, node):

        for child in node.children:

            self.nodes.append(child)

            if child.children:
                self._walk(child)

    # -------------------------------------------------

    def current(self):

        if self.index < 0 or self.index >= len(self.nodes):
            return None

        return self.nodes[self.index]

    # -------------------------------------------------

    def next(self):

        if not self.nodes:
            return None

        self.index = min(self.index + 1, len(self.nodes) - 1)

        return self.current()

    # -------------------------------------------------

    def previous(self):

        if not self.nodes:
            return None

        self.index = max(self.index - 1, 0)

        return self.current()

    # -------------------------------------------------

    def find_next(self, role):
        
        start = self.index + 1

        for i in range(start, len(self.nodes)):

            if self.nodes[i].role == role:
                self.index = i
                return self.nodes[i]

        return None