from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional

from .intent_schema import Intent


@dataclass
class ConversationTurn:
    user_text: str
    assistant_text: str = ""
    action: Optional[str] = None
    target: Optional[str] = None
    entities: Dict[str, str] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ContextMemory:
    """
    Production-ready conversational memory with follow-up resolution.
    """

    FOLLOW_UP_PATTERNS = [
        r"^(and|then)\b",
        r"^(do it|do that|open it|close it)\b",
        r"^(what about|how about)\b",
        r"^(search for|find)\b",
        r"^(click it|press it|select it)\b",
    ]

    REFERENCE_WORDS = {"it", "that", "this", "them", "those", "there"}

    def __init__(self, max_history: int = 20):
        self.session_id: str = str(int(time.time()))
        self.max_history = max_history
        self.history: List[Intent] = []
        self.turns: List[ConversationTurn] = []

        self.last_app: Optional[str] = None
        self.last_file: Optional[str] = None
        self.last_topic: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_target: Optional[str] = None
        self.pending_goal: Optional[str] = None
        self.global_entities: Dict[str, str] = {}

        self.lock = Lock()

    def enrich(self, intent: Intent) -> Intent:
        with self.lock:
            normalized_text = intent.text.lower().strip()
            intent.context.setdefault("session_id", self.session_id)
            intent.context["conversation_state"] = self._conversation_state()

            if self.is_follow_up(normalized_text):
                intent.context["is_follow_up"] = True
                if self.last_action and intent.action in {"UNKNOWN", "SEARCH"}:
                    intent.context["previous_action"] = self.last_action

            if intent.target:
                resolved = self.resolve_reference(intent.target)
                if resolved and resolved != intent.target:
                    intent.target = resolved
                    intent.parameters["target"] = resolved
                    intent.context["reference_resolved"] = True

            if not intent.target:
                inferred_target = self._infer_target(intent, normalized_text)
                if inferred_target:
                    intent.target = inferred_target
                    intent.parameters.setdefault("target", inferred_target)
                    intent.context["inferred_from_context"] = True

            if intent.action == "SEARCH" and not intent.target and self.last_topic:
                intent.target = self.last_topic
                intent.parameters["target"] = self.last_topic
                intent.context["inferred_from"] = "last_topic"
                intent.context["inference_confidence"] = 0.8

            if intent.action in {"KNOWLEDGE_QUERY", "GET_TIME"} and self.last_topic:
                intent.context.setdefault("previous_topic", self.last_topic)

            if not intent.context.get("topic") and self.last_topic:
                intent.context["topic"] = self.last_topic

            if self.global_entities:
                intent.context["entities"] = dict(self.global_entities)

        return intent

    def update(self, intent: Intent) -> None:
        with self.lock:
            self.history.append(intent)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            self.last_action = intent.action
            self.last_target = intent.target or self.last_target

            if intent.action == "OPEN_APP" and intent.target:
                self.last_app = intent.target

            if intent.action == "SYSTEM_CONTROL" and intent.target and self.last_app == intent.target:
                self.last_app = None

            if intent.action in ["DELETE", "FILE_OPERATION", "OPEN_FILE"] and intent.target:
                self.last_file = intent.target

            topic = self._extract_topic(intent)
            if topic:
                self.last_topic = topic

            self._update_entities_from_intent(intent)

    def record_turn(
        self,
        user_text: str,
        assistant_text: str,
        *,
        action: Optional[str] = None,
        target: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        with self.lock:
            turn = ConversationTurn(
                user_text=user_text,
                assistant_text=assistant_text,
                action=action,
                target=target,
                entities=dict(self.global_entities),
                metadata=metadata or {},
            )
            self.turns.append(turn)
            if len(self.turns) > self.max_history:
                self.turns.pop(0)

    def is_follow_up(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in self.FOLLOW_UP_PATTERNS)

    def resolve_reference(self, target: Optional[str]) -> Optional[str]:
        if not target:
            return target

        normalized = target.lower().strip()
        if normalized in self.REFERENCE_WORDS:
            return self.last_app or self.last_file or self.last_target or self.last_topic
        return target

    def get_last_intent(self) -> Optional[Intent]:
        if not self.history:
            return None
        return self.history[-1]

    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        return self.turns[-count:]

    def get_context_prompt(self, count: int = 3) -> str:
        with self.lock:
            turns = self.get_recent_turns(count)
            if not turns:
                return ""

            lines = []
            for turn in turns:
                lines.append(f"User: {turn.user_text}")
                lines.append(f"Assistant: {turn.assistant_text}")

            if self.global_entities:
                lines.append("Known entities:")
                for key, value in self.global_entities.items():
                    lines.append(f"{key}: {value}")

            if self.last_topic:
                lines.append(f"Current topic: {self.last_topic}")

            return "\n".join(lines)

    def clear(self) -> None:
        with self.lock:
            self.history.clear()
            self.turns.clear()
            self.last_app = None
            self.last_file = None
            self.last_topic = None
            self.last_action = None
            self.last_target = None
            self.pending_goal = None
            self.global_entities = {}

    def get_memory_snapshot(self) -> Dict:
        return {
            "session_id": self.session_id,
            "last_app": self.last_app,
            "last_file": self.last_file,
            "last_topic": self.last_topic,
            "last_action": self.last_action,
            "last_target": self.last_target,
            "history_size": len(self.history),
            "turns_size": len(self.turns),
            "entities": dict(self.global_entities),
        }

    def _conversation_state(self) -> str:
        if self.pending_goal:
            return "goal_active"
        if self.turns:
            return "in_conversation"
        return "fresh"

    def _infer_target(self, intent: Intent, normalized_text: str) -> Optional[str]:
        if intent.action == "SEARCH" and self.last_topic:
            return self.last_topic
        if intent.action == "CLICK_NAME" and self.last_target:
            return self.last_target
        if self.is_follow_up(normalized_text):
            return self.last_target or self.last_app or self.last_file or self.last_topic
        return None

    def _extract_topic(self, intent: Intent) -> Optional[str]:
        if intent.target:
            return intent.target
        if intent.action in {"KNOWLEDGE_QUERY", "SEARCH"}:
            return intent.text
        return self.last_topic

    def _update_entities_from_intent(self, intent: Intent) -> None:
        if intent.target:
            entity_key = f"{intent.action}_TARGET"
            self.global_entities[entity_key] = intent.target

        if intent.action == "OPEN_APP" and intent.target:
            self.global_entities["APP"] = intent.target
        elif intent.action in {"FILE_OPERATION", "DELETE"} and intent.target:
            self.global_entities["FILE"] = intent.target
        elif intent.action in {"SEARCH", "KNOWLEDGE_QUERY"}:
            topic = intent.target or intent.text
            if topic:
                self.global_entities["TOPIC"] = topic
