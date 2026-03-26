# vision/screen_element.py

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class ScreenElement:
    """
    Unified representation of a screen element.
    Can originate from UIA, OCR, or Vision detection.
    """

    element_id: int
    name: str
    element_type: str
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    source: str  # UIA | OCR | VISION
    attributes: Optional[Dict[str, str]] = None

    # =====================================================
    # GEOMETRY
    # =====================================================

    def center(self):
        """Return center point of bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def width(self):
        x1, _, x2, _ = self.bbox
        return abs(x2 - x1)

    def height(self):
        _, y1, _, y2 = self.bbox
        return abs(y2 - y1)

    def area(self):
        return self.width() * self.height()

    # =====================================================
    # DEBUG HELPERS
    # =====================================================

    def to_dict(self):
        return {
            "id": self.element_id,
            "name": self.name,
            "type": self.element_type,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "source": self.source,
            "attributes": self.attributes or {},
        }

    def __repr__(self):
        return f"<ScreenElement {self.name} ({self.source})>"
