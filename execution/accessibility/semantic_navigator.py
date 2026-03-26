from difflib import SequenceMatcher, get_close_matches
import re


class SemanticNavigator:
    """
    Semantic Navigation Engine

    Enables commands like:
    - next button
    - next input
    - next link
    """

    ROLE_MAP = {
        "button": {"button", "Button"},
        "input": {"edit", "Edit", "textarea"},
        "link": {"link", "Link"},
        "tab": {"tabitem", "TabItem"},
        "menu": {"menuitem", "MenuItem"}
    }

    # =====================================================

    def __init__(self, tree):

        self.tree = tree

    # =====================================================
    # SAFE ELEMENT LIST
    # =====================================================

    def _elements(self):

        if not hasattr(self.tree, "elements"):
            return []

        return self.tree.elements

    # =====================================================
    # FIND NEXT ELEMENT BY TYPE
    # =====================================================

    def next_by_type(self, element_type):

        roles = self.ROLE_MAP.get(element_type.lower())

        if not roles:
            return None

        elements = self._elements()

        if not elements:
            return None

        start = self.tree.index + 1

        # Forward search
        for i in range(start, len(elements)):

            el = elements[i]

            if getattr(el, "control_type", "").lower() in {
                r.lower() for r in roles
            }:

                self.tree.index = i
                return el

        # Wrap-around search
        for i in range(0, start):

            el = elements[i]

            if getattr(el, "control_type", "").lower() in {
                r.lower() for r in roles
            }:

                self.tree.index = i
                return el

        return None

    def find_element_by_name(self, elements, name):
        normalized_target = self._normalize_name(name)
        alias_map = {}

        for element in elements:
            for alias in self._aliases(element):
                alias_map[alias] = element
                if normalized_target and normalized_target in alias:
                    return element

        if not alias_map:
            return None

        matches = get_close_matches(
            normalized_target,
            list(alias_map.keys()),
            n=3,
            cutoff=0.6,
        )
        if not matches:
            return None

        best = max(
            matches,
            key=lambda candidate: SequenceMatcher(None, normalized_target, candidate).ratio(),
        )
        return alias_map.get(best)

    def _normalize_name(self, value):
        normalized = re.sub(r"[^\w\s]", "", (value or "").lower()).strip()
        tokens = []
        for token in normalized.split():
            if token.endswith("s") and len(token) > 3:
                token = token[:-1]
            tokens.append(token)
        return " ".join(tokens)

    def _aliases(self, element):
        normalized = self._normalize_name(getattr(element, "name", ""))
        aliases = {normalized}
        stripped = [
            token for token in normalized.split()
            if token not in {"button", "menu", "item", "tab", "control"}
        ]
        if stripped:
            aliases.add(" ".join(stripped))
        for token in stripped or normalized.split():
            aliases.add(token)
        return [alias for alias in aliases if alias]
