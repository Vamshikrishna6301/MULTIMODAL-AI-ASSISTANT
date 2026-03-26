class OutputFilter:
    """
    Filters navigator output to remove duplicates and UI noise.
    """

    NOISE_PATTERNS = {
        "ctrl+",
        "toggle",
        "memory usage",
        "pinned",
        "customize layout",
        "views and more actions",
        "pending changes",
        "accounts",
        "manage",
    }

    def __init__(self):
        self.seen = set()

    def clean(self, text):

        if not text:
            return None

        lower = text.lower()

        # ignore noise patterns
        for pattern in self.NOISE_PATTERNS:
            if pattern in lower:
                return None

        # ignore tiny labels
        if len(text) < 3:
            return None

        # ignore duplicates
        if text in self.seen:
            return None

        self.seen.add(text)

        return text