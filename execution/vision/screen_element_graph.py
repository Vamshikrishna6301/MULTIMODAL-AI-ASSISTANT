# vision/screen_element_graph.py

from typing import List
from execution.vision.screen_element import ScreenElement


class ScreenElementGraph:
    """
    Combines UIA, OCR, and Vision detections
    into a unified screen element graph.
    """

    def __init__(self):
        self.elements: List[ScreenElement] = []
        self._next_id = 1

    # -----------------------------------------------------

    def add_element(self, name, element_type, bbox, confidence, source, attributes=None):

        element = ScreenElement(
            element_id=self._next_id,
            name=name.lower().strip(),
            element_type=element_type,
            bbox=bbox,
            confidence=confidence,
            source=source,
            attributes=attributes or {}
        )

        self.elements.append(element)
        self._next_id += 1

    # -----------------------------------------------------

    def get_elements(self) -> List[ScreenElement]:
        return list(self.elements)

    # -----------------------------------------------------

    def find_by_name(self, name: str) -> List[ScreenElement]:

        name = name.lower()

        return [
            e for e in self.elements
            if name in e.name
        ]

    # -----------------------------------------------------

    def clear(self):
        self.elements.clear()
        self._next_id = 1
