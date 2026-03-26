class PerceptionFilter:
    """
    Filters noisy UIA elements into useful accessibility controls.
    Prevents terminal/editor text from being treated as UI controls.
    """

    ALLOWED_TYPES = {
        "Button",
        "Hyperlink",
        "MenuItem",
        "TabItem",
        "Edit",
        "CheckBox",
        "RadioButton",
        "ComboBox",
        "ListItem"
    }

    NOISE_PATTERNS = {
        "toggle screen reader",
        "run the command",
        "terminal accessibility help",
        "python run the command",
        "good — this error",
        "copy ",
        "python copy run code"
    }

    MAX_TEXT_LENGTH = 80

    def filter_elements(self, elements):

        filtered = []

        for el in elements:

            name = el.get("name", "").strip()
            control_type = el.get("type", "")

            if not name:
                continue

            # Ignore non-interactive types
            if control_type not in self.ALLOWED_TYPES:
                continue

            # Ignore extremely short labels
            if len(name) < 2:
                continue

            # Ignore long terminal/editor text
            if len(name) > self.MAX_TEXT_LENGTH:
                continue

            # Ignore common noise patterns
            lower = name.lower()
            if any(pattern in lower for pattern in self.NOISE_PATTERNS):
                continue

            # Ignore trivial symbols
            if name in {"x", "+", "|", "€"}:
                continue

            filtered.append({
                "name": name,
                "type": control_type
            })

        return filtered