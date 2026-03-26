import re
import time
from typing import Optional, Tuple

from core.intent_schema import (
    Intent,
    IntentType,
    Mode
)
from execution.plugin_system import get_plugin_manager
from infrastructure.logger import get_logger


class IntentParser:
    """
    Deterministic production intent parser.
    """

    def __init__(self):
        self.plugin_manager = get_plugin_manager()
        self.logger = get_logger("core.intent_parser")

        self.command_keywords = {
        "open": (IntentType.OPEN_APP, 1),
        "launch": (IntentType.OPEN_APP, 1),
        "start": (IntentType.OPEN_APP, 1),
        "run": (IntentType.OPEN_APP, 1),

        "close": (IntentType.SYSTEM_CONTROL, 2),
        "exit": (IntentType.SYSTEM_CONTROL, 2),

        "delete": (IntentType.FILE_OPERATION, 8),
        "remove": (IntentType.FILE_OPERATION, 8),

        "shutdown": (IntentType.SYSTEM_CONTROL, 9),
        "restart": (IntentType.SYSTEM_CONTROL, 7),

        "search": (IntentType.SEARCH, 1),

        "type": (IntentType.TYPE_TEXT, 1),
        "write": (IntentType.TYPE_TEXT, 1),
    }
        self.filler_words = {
            "the", "a", "an", "please", "for", "to",
            "about", "can", "you", "could", "would",
            "hey", "assistant", "my"
        }

    # =====================================================
    # MAIN PARSER
    # =====================================================

    def parse(self, text: str, current_mode: Mode = Mode.COMMAND) -> Intent:

        timestamp = time.time()
        original_text = text
        text = self._normalize(text)

        if text.count("open") > 1:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                text=original_text,
                action="UNKNOWN",
                confidence=0.2,
                confidence_source="multi_command_filter",
                risk_level=0,
                timestamp=timestamp
            )

        plugin_match = self.plugin_manager.match_intent(text)
        if plugin_match:
            parameters = dict(plugin_match.parameters)
            parameters["plugin_id"] = plugin_match.plugin_id
            parameters["plugin_action"] = plugin_match.plugin_action
            if plugin_match.target:
                parameters.setdefault("target", plugin_match.target)
            return Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="PLUGIN",
                target=plugin_match.target,
                parameters=parameters,
                confidence=plugin_match.confidence,
                confidence_source="plugin_registry",
                risk_level=plugin_match.risk_level,
                requires_confirmation=plugin_match.requires_confirmation,
                timestamp=timestamp,
            )

        # --------------------------------------------------
        # GREETING
        # --------------------------------------------------

        if re.fullmatch(r"(hello|hi|hey|start assistant|are you there)", text):
            intent = Intent(
                intent_type=IntentType.QUESTION,
                text=original_text,
                action="GREETING",
                confidence=0.9,
                confidence_source="greeting_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        if text in {"describe screen", "describe the screen"}:
            intent = Intent(
                intent_type=IntentType.QUERY,
                text=original_text,
                action="DESCRIBE_CONTEXT",
                confidence=0.95,
                confidence_source="context_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        if text == "focus search":
            intent = Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="FOCUS_INPUT",
                confidence=0.92,
                confidence_source="focus_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        if text.startswith("focus "):
            target_name = text.replace("focus", "", 1).strip()
            intent = Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="FOCUS_NAME",
                parameters={"name": target_name},
                confidence=0.92,
                confidence_source="focus_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        if "where is" in text:
            obj = text.replace("where is", "").strip()

            intent = Intent(
                intent_type=IntentType.QUERY,
                text=original_text,
                action="QUERY_OBJECT",
                parameters={"object": obj},
                confidence=0.95,
                confidence_source="object_query_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        # --------------------------------------------------
        # READ SCREEN
        # --------------------------------------------------

        if re.search(r"(read what is on my screen|look at the screen|describe the screen)", text):
            return Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="VISION",
                target="screen",
                parameters={"task": "read_text" if "read" in text else "describe"},
                confidence=0.95,
                confidence_source="vision_rule",
                risk_level=0,
                timestamp=timestamp
            )

        if re.search(r"(read screen|what is on my screen|whats on my screen|what is on screen|describe screen|describe my screen|show screen)",text):
            return self._intent(original_text, "READ_SCREEN", timestamp)

        if re.search(r"(what is this|what is focused|read current|read current line|read focused element)", text):
            return self._intent(original_text, "READ_CURRENT", timestamp)

        # --------------------------------------------------
        # NAVIGATION
        # --------------------------------------------------

        if "next button" in text:
            return self._intent(original_text, "NEXT_BUTTON", timestamp)

        if "next input field" in text or "next input" in text:
            return self._intent(original_text, "NEXT_INPUT", timestamp)

        if "next link" in text:
            return self._intent(original_text, "NEXT_LINK", timestamp)

        if "open menu" in text:
            return self._intent(original_text, "NEXT_MENU", timestamp)

        if re.search(r"\b(next|next item|move next|go next|next element)\b", text):
            return self._intent(original_text, "NEXT_ITEM", timestamp)

        if re.search(r"\b(previous|previous item|go back|move back|previous element)\b", text):
            return self._intent(original_text, "PREVIOUS_ITEM", timestamp)

        if re.fullmatch(r"(activate|press|click)", text):
            return self._intent(original_text, "ACTIVATE_ITEM", timestamp)

        # --------------------------------------------------
        # CLICK INDEX
        # --------------------------------------------------

        match = re.search(r"(click|select)\s+(\d+)", text)

        if match:

            index = int(match.group(2))

            return Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="CLICK_INDEX",
                parameters={"index": index},
                confidence=0.95,
                confidence_source="index_rule",
                risk_level=0,
                timestamp=timestamp
            )

        match = re.search(r"(click|press|select)\s+(.+)", text)

        if match:

            query = match.group(2).strip()
            vision_tokens = {"icon", "button", "link", "menu", "tab"}
            color_tokens = {
                "red", "green", "blue", "yellow", "orange",
                "purple", "pink", "black", "white", "gray",
                "grey", "brown"
            }

            if any(token in query.split() for token in vision_tokens | color_tokens):
                return Intent(
                    intent_type=IntentType.CONTROL,
                    text=original_text,
                    action="VISION",
                    target="screen",
                    parameters={"task": "click", "query": query},
                    confidence=0.92,
                    confidence_source="vision_click_rule",
                    risk_level=0,
                    timestamp=timestamp
                )

            return Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="CLICK_NAME",
                parameters={"name": query},
                confidence=0.9,
                confidence_source="name_rule",
                risk_level=0,
                timestamp=timestamp
            )

        if "stop camera" in text or "close camera" in text:
            intent = Intent(
                intent_type=IntentType.EXECUTION,
                text=original_text,
                action="STOP_SCENE_UNDERSTANDING",
                parameters={},
                confidence=0.95,
                confidence_source="camera_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        if "camera" in text or "scene" in text or "see around" in text:
            intent = Intent(
                intent_type=IntentType.EXECUTION,
                text=original_text,
                action="START_SCENE_UNDERSTANDING",
                parameters={},
                confidence=0.95,
                confidence_source="camera_rule",
                risk_level=0,
                timestamp=timestamp
            )
            self._log_intent(text, intent)
            return intent

        # --------------------------------------------------
        # TIME QUERY
        # --------------------------------------------------

        if re.search(r"(what time|current time|time now)", text):
            return self._intent(original_text, "GET_TIME", timestamp)

        # --------------------------------------------------
        # CALCULATION (checked BEFORE knowledge)
        # --------------------------------------------------



        calc_simple = re.search(
            r"(\d+)\s*(plus|minus|times|divided by|\+|\-|\*|\/)\s*(\d+)",
            text
        )

        if calc_simple:

            expr = text
            expr = expr.replace("plus", "+")
            expr = expr.replace("minus", "-")
            expr = expr.replace("times", "*")
            expr = expr.replace("divided by", "/")

            expr = re.sub(r"[^\d\+\-\*\/\s]", "", expr).strip()

            return Intent(
                intent_type=IntentType.CONTROL,
                text=original_text,
                action="CALCULATE",
                parameters={"expression": expr},
                confidence=0.95,
                confidence_source="calc_rule",
                risk_level=0,
                timestamp=timestamp
            )

        # --------------------------------------------------
        # KNOWLEDGE QUERY
        # --------------------------------------------------

        if (
    re.search(r"(who is|who was|what is|what was|tell me about|define)", text)
    and "screen" not in text
    and "display" not in text
):
            return Intent(
                intent_type=IntentType.QUESTION,
                text=original_text,
                action="KNOWLEDGE_QUERY",
                target=original_text,
                confidence=0.9,
                confidence_source="knowledge_rule",
                risk_level=0,
                timestamp=timestamp
            )

        # --------------------------------------------------
        # GENERIC COMMANDS
        # --------------------------------------------------

        intent_type, risk_level, keyword = self._detect_command(text)

        if intent_type:

            target = self._extract_target(text, keyword)

            return Intent(
                intent_type=intent_type,
                text=original_text,
                action=intent_type.name,
                target=target,
                parameters={"target": target} if target else {},
                confidence=0.95,
                confidence_source="keyword_rule",
                risk_level=risk_level,
                requires_confirmation=risk_level >= 7,
                timestamp=timestamp
            )

        # --------------------------------------------------
        # FALLBACK
        # --------------------------------------------------

        return Intent(
            intent_type=IntentType.UNKNOWN,
            text=original_text,
            action="UNKNOWN",
            confidence=0.3,
            confidence_source="fallback",
            risk_level=0,
            timestamp=timestamp
        )

    # =====================================================
    # HELPERS
    # =====================================================

    def _intent(self, text, action, timestamp):

        return Intent(
            intent_type=IntentType.CONTROL,
            text=text,
            action=action,
            confidence=0.98,
            confidence_source="deterministic_rule",
            risk_level=0,
            timestamp=timestamp
        )

    def _detect_command(self, text: str) -> Tuple[Optional[IntentType], int, Optional[str]]:

        for keyword, value in self.command_keywords.items():

            if keyword in text:
                return value[0], value[1], keyword

        return None, 0, None

    def _extract_target(self, text: str, keyword: str):

        parts = text.split(keyword, 1)

        if len(parts) < 2:
            return None

        tokens = parts[1].strip().split()

        cleaned = [t for t in tokens if t not in self.filler_words]

        return " ".join(cleaned).strip() or None

    def _normalize(self, text):

        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)

        return text

    def _log_intent(self, text: str, intent: Intent) -> None:
        try:
            self.logger.debug(
                "intent_mapping",
                text=text,
                action=intent.action,
                intent_type=intent.intent_type.name,
            )
        except Exception:
            pass
