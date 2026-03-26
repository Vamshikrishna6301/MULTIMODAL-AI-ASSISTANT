from __future__ import annotations

from typing import List, Optional, Tuple

from execution.vision.grounding import VisionGrounder
from execution.vision.screen_element import ScreenElement


class ElementSelector:
    """
    Ranks OCR, UIA, and visual detections against a grounded query.
    """

    SOURCE_WEIGHTS = {
        "UIA": 1.0,
        "OCR": 0.85,
        "VISION": 0.7,
    }

    def __init__(self):
        self.grounder = VisionGrounder()

    def select_best(self, query: str, elements: List[ScreenElement]) -> Optional[ScreenElement]:
        ranked = self.rank(query, elements)
        return ranked[0][0] if ranked else None

    def rank(self, query: str, elements: List[ScreenElement]) -> List[Tuple[ScreenElement, float]]:
        if not query or not elements:
            return []

        grounding = self.grounder.parse(query)
        ranked: List[Tuple[ScreenElement, float]] = []

        for element in elements:
            score = self._score_element(grounding, element)
            if score <= 0:
                continue
            ranked.append((element, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _score_element(self, grounding, element: ScreenElement) -> float:
        name = (element.name or "").lower()
        element_type = (element.element_type or "").lower()
        attributes = element.attributes or {}
        score = float(element.confidence) * 2.5
        score += self.SOURCE_WEIGHTS.get(element.source, 0.5)

        if grounding.normalized_text and grounding.normalized_text in name:
            score += 5.0

        token_hits = 0
        for token in grounding.label_tokens:
            if token in name:
                token_hits += 1
                score += 2.0
            elif token in (attributes.get("ocr_text", "").lower()):
                token_hits += 1
                score += 1.5

        if grounding.label_tokens and token_hits == 0 and grounding.desired_type is None and grounding.color is None:
            return 0.0

        semantic_role = (attributes.get("semantic_role") or "").lower()
        dominant_color = (attributes.get("dominant_color") or "").lower()

        if grounding.desired_type:
            if grounding.desired_type in element_type or grounding.desired_type in semantic_role:
                score += 2.0
            elif grounding.desired_type == "button" and element.source == "VISION":
                score += 0.5
            else:
                score -= 1.5

        if grounding.color:
            if grounding.color == dominant_color:
                score += 2.0
            else:
                score -= 0.75

        if element.area() > 0:
            score += min(element.area() / 12000.0, 1.5)

        return round(score, 3)
