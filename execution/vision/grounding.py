from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set


@dataclass
class GroundingQuery:
    raw_text: str
    normalized_text: str
    label_tokens: Set[str]
    color: Optional[str] = None
    desired_type: Optional[str] = None


class VisionGrounder:
    """
    Parses grounded natural-language references like:
    - click login button
    - click red icon
    """

    COLORS = {
        "red", "green", "blue", "yellow", "orange",
        "black", "white", "gray", "grey", "purple",
        "pink", "brown",
    }

    TYPE_ALIASES = {
        "button": "button",
        "btn": "button",
        "icon": "icon",
        "link": "link",
        "textbox": "input",
        "input": "input",
        "field": "input",
        "menu": "menu",
        "tab": "tab",
    }

    STOP_WORDS = {
        "click", "press", "the", "a", "an", "on", "to", "that", "this",
    }

    def parse(self, query: Optional[str]) -> GroundingQuery:
        raw = (query or "").strip()
        normalized = raw.lower().strip()
        tokens = [token for token in normalized.split() if token]

        color = next((token for token in tokens if token in self.COLORS), None)
        desired_type = next((self.TYPE_ALIASES[token] for token in tokens if token in self.TYPE_ALIASES), None)
        label_tokens = {
            token for token in tokens
            if token not in self.STOP_WORDS and token not in self.COLORS and token not in self.TYPE_ALIASES
        }

        return GroundingQuery(
            raw_text=raw,
            normalized_text=normalized,
            label_tokens=label_tokens,
            color=color,
            desired_type=desired_type,
        )
