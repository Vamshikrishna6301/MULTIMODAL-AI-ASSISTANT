class UIElement:
    """
    Universal accessibility element representation.

    Works for:
    • Windows UI Automation
    • Browser DOM
    • Vision detection (future)
    """

    def __init__(
        self,
        name=None,
        control_type=None,
        index=None,
        bbox=None,
        selector=None,
        region=None
    ):

        self.name = name or ""
        self.control_type = control_type or ""
        self.index = index
        self.bbox = bbox

        # Browser-specific
        self.selector = selector
        self.region = region

    # =====================================================
    # SPEECH REPRESENTATION
    # =====================================================

    def speakable(self):

        role = self.control_type

        if not role:
            role = "Element"

        if not self.name:
            return role

        return f"{role} {self.name}"

    # =====================================================
    # TYPE HELPERS
    # =====================================================

    def is_button(self):

        return "button" in self.control_type.lower()

    def is_input(self):

        return any(
            x in self.control_type.lower()
            for x in ["edit", "textarea", "input"]
        )

    def is_link(self):

        return "link" in self.control_type.lower()

    # =====================================================
    # REGION HELPERS
    # =====================================================

    def in_sidebar(self):

        return self.region == "sidebar"

    def in_main(self):

        return self.region == "main"

    def in_input(self):

        return self.region == "input"