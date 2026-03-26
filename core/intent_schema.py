"""
Intent Schema - Phase 2 Production Upgrade

Structured, execution-ready, multimodal-compatible intent representation.
Designed for deterministic AI assistant architecture.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any
import time
import uuid


# ==============================
# INTENT TYPES (Execution Level)
# ==============================

class IntentType(Enum):
    EXECUTION = auto()
    QUERY = auto()
    OPEN_APP = auto()
    SEARCH = auto()
    TYPE_TEXT = auto()
    CLICK = auto()
    SCROLL = auto()
    FILE_OPERATION = auto()
    SYSTEM_CONTROL = auto()
    QUESTION = auto()
    DICTATION = auto()
    CONTROL = auto()
    UNKNOWN = auto()


# ==============================
# MODES (Conversation Level)
# ==============================

class Mode(Enum):
    COMMAND = auto()
    DICTATION = auto()
    QUESTION = auto()
    DISABLED = auto()
    LISTENING = auto()


# ==============================
# CONFIDENCE LEVELS
# ==============================

class ConfidenceLevel(Enum):
    HIGH = 0.90
    MEDIUM = 0.75
    LOW = 0.50


# ==============================
# ENTITY
# ==============================

@dataclass
class Entity:
    name: str
    value: str
    confidence: float
    entity_type: str = "keyword"

    def is_valid(self) -> bool:
        return 0.0 <= self.confidence <= 1.0


# ==============================
# INTENT
# ==============================

@dataclass
class Intent:
    intent_type: IntentType
    text: str

    action: str
    target: Optional[str] = None

    parameters: Dict[str, Any] = field(default_factory=dict)

    confidence: float = 0.5
    confidence_source: str = "unknown"

    entities: Dict[str, Entity] = field(default_factory=dict)

    context: Dict[str, Any] = field(default_factory=dict)
    mode: Mode = Mode.COMMAND

    requires_confirmation: bool = False
    risk_level: int = 0
    blocked_reason: Optional[str] = None

    timestamp: float = field(default_factory=time.time)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ==============================
    # VALIDATION
    # ==============================

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        if not 0 <= self.risk_level <= 10:
            raise ValueError("Risk level must be between 0-10")

    # ==============================
    # HELPER METHODS
    # ==============================

    def is_high_confidence(self) -> bool:
        return self.confidence >= ConfidenceLevel.HIGH.value

    def is_medium_confidence(self) -> bool:
        return ConfidenceLevel.MEDIUM.value <= self.confidence < ConfidenceLevel.HIGH.value

    def is_low_confidence(self) -> bool:
        return self.confidence < ConfidenceLevel.MEDIUM.value

    def is_dangerous(self) -> bool:
        return self.risk_level >= 7

    def is_blocked(self) -> bool:
        return self.blocked_reason is not None

    def needs_clarification(self) -> bool:
        return self.is_low_confidence() or self.intent_type == IntentType.UNKNOWN

    def is_executable(self) -> bool:
        return (
            not self.is_blocked()
            and self.intent_type not in [IntentType.UNKNOWN, IntentType.DICTATION, IntentType.QUESTION]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.name,
            "text": self.text,
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "mode": self.mode.name,
            "requires_confirmation": self.requires_confirmation,
            "risk_level": self.risk_level,
            "blocked_reason": self.blocked_reason,
            "timestamp": self.timestamp,
            "session_id": self.session_id
        }


# ==============================
# INTENT BUFFER
# ==============================

@dataclass
class IntentBuffer:
    intents: List[Intent] = field(default_factory=list)
    max_size: int = 10
    timeout_secs: int = 5

    def add(self, intent: Intent) -> None:
        self.intents.append(intent)
        if len(self.intents) > self.max_size:
            self.intents.pop(0)

    def get_recent(self, count: int = 3) -> List[Intent]:
        return self.intents[-count:]

    def has_conflict(self) -> bool:
        if len(self.intents) < 2:
            return False

        recent = self.get_recent(2)
        return (
            recent[0].intent_type != recent[1].intent_type
            and recent[0].action != recent[1].action
        )
