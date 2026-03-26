import win32gui


class SemanticScreenAnalyzer:

    def analyze(self, window_title, focused_element):

        description = []

        if window_title:
            description.append(f"You are in {window_title}.")

        if not focused_element:
            return " ".join(description)

        role = getattr(focused_element, "role", "")
        name = getattr(focused_element, "name", "")

        if role == "Edit":
            description.append("You are in an input field.")

        if role == "Document":
            description.append("A document editor is open.")

        if role == "MenuItem":
            description.append("You are navigating a menu.")

        if role == "Button":
            description.append(f"Button {name} is focused.")

        if role == "Edit" and name:
            description.append(f"{name} focused.")

        return " ".join(description)
