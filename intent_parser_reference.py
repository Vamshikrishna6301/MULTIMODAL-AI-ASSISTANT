"""
Reference Implementation: Intent Parser with Multi-Layered Confidence Scoring
Based on patterns from Mycroft AI, Home Assistant, and OpenAssistant

This module demonstrates how to build a production-ready intent parsing system
with confidence scoring, safety validation, and state management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Callable, Any
from abc import ABC, abstractmethod
import re


# ============================================================================
# 1. INTENT REPRESENTATION LAYER
# ============================================================================

class IntentType(Enum):
    """Available intent types (like Home Assistant predefined intents)"""
    TURN_ON = "HassTurnOn"
    TURN_OFF = "HassTurnOff"
    GET_STATE = "HassGetState"
    SET_LEVEL = "HassSetLevel"
    PLAY_MEDIA = "HassPlayMedia"
    CONTEXT_HELP = "ContextHelp"
    MODE_CHANGE = "ModeChange"


@dataclass
class IntentMatch:
    """Result of intent parsing (Mycroft style)"""
    intent_type: IntentType
    confidence: float  # 0.0-1.0
    entities: Dict[str, str]  # Extracted slot values
    source: str  # "keyword", "ml_classifier", "context"
    context: Optional[Dict[str, Any]] = None
    
    def requires_confirmation(self) -> bool:
        """Confidence gating: Check if user confirmation needed"""
        return 0.5 <= self.confidence < 0.8
    
    def requires_clarification(self) -> bool:
        """Confidence gating: Check if clarification needed"""
        return self.confidence < 0.5
    
    def can_execute_immediately(self) -> bool:
        """Confidence gating: Check if can execute without confirmation"""
        return self.confidence >= 0.95


@dataclass
class MatchTargetsConstraints:
    """Constraint-based targeting (Home Assistant style)"""
    entity_domains: Optional[List[str]] = None  # e.g., ['light', 'switch']
    device_features: Optional[List[str]] = None  # e.g., ['brightness']
    entity_states: Optional[List[str]] = None  # e.g., ['on', 'off']
    area_name: Optional[str] = None
    require_single_target: bool = False


# ============================================================================
# 2. ENTITY EXTRACTION LAYER (Multi-method strategy)
# ============================================================================

class EntityExtractor(ABC):
    """Base class for entity extraction methods"""
    
    @abstractmethod
    def extract(self, text: str) -> Dict[str, str]:
        """Extract entities from text. Dict keys are entity names."""
        pass


class KeywordEntityExtractor(EntityExtractor):
    """Fast O(1) keyword matching (vocabulary-based)"""
    
    def __init__(self):
        self.vocabulary: Dict[str, List[str]] = {}
        # Build trie-like structure
        self.entity_trie: Dict = {}
    
    def register_entity(self, entity_type: str, values: List[str]):
        """Register vocabulary: entity_type -> [values]"""
        self.vocabulary[entity_type] = values
        for value in values:
            self._add_to_trie(value, entity_type)
    
    def _add_to_trie(self, word: str, entity_type: str):
        """Add word to trie structure"""
        node = self.entity_trie
        for char in word.lower():
            if char not in node:
                node[char] = {}
            node = node[char]
        node['__type__'] = entity_type
    
    def extract(self, text: str) -> Dict[str, str]:
        """Match keywords in text"""
        results = {}
        text_lower = text.lower()
        
        # Simple substring matching (production would use proper tokenization)
        for entity_type, values in self.vocabulary.items():
            for value in values:
                if value.lower() in text_lower:
                    results[entity_type] = value
                    break
        
        return results


class RegexEntityExtractor(EntityExtractor):
    """Pattern-based extraction with named groups"""
    
    def __init__(self):
        self.patterns: Dict[str, str] = {}
    
    def register_pattern(self, entity_type: str, regex_pattern: str):
        """Register regex pattern (like Mycroft .rx files)"""
        self.patterns[entity_type] = regex_pattern
    
    def extract(self, text: str) -> Dict[str, str]:
        """Extract entities using regex patterns"""
        results = {}
        
        for entity_type, pattern in self.patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    results[entity_type] = match.groupdict()
                except IndexError:
                    results[entity_type] = match.group(1)
        
        return results


class ContextEntityExtractor(EntityExtractor):
    """Extract entities from conversation history"""
    
    def __init__(self, context_manager: 'ContextManager'):
        self.context = context_manager
    
    def extract(self, text: str) -> Dict[str, str]:
        """Use latest context frame for entity inference"""
        results = {}
        
        # Get last frame from context
        if self.context.frame_stack:
            last_frame = self.context.frame_stack[-1]
            # Re-inject previous entities if not contradicted
            results.update(last_frame.get('entities', {}))
        
        return results


# ============================================================================
# 3. CONFIDENCE SCORING LAYER (Multi-tier like Mycroft)
# ============================================================================

class IntentClassifier(ABC):
    """Base class for intent classifiers"""
    confidence_threshold: float
    
    @abstractmethod
    def classify(self, utterance: str, entities: Dict[str, str]) -> Optional[IntentMatch]:
        """Classify intent from utterance and extracted entities"""
        pass


class KeywordIntentClassifier(IntentClassifier):
    """Fast keyword-based classifier (Adapt style)"""
    confidence_threshold = 0.95
    
    def __init__(self):
        self.intent_patterns: Dict[IntentType, List[str]] = {}
    
    def register_intent(self, intent_type: IntentType, keywords: List[str]):
        """Register intent keywords"""
        self.intent_patterns[intent_type] = keywords
    
    def classify(self, utterance: str, entities: Dict[str, str]) -> Optional[IntentMatch]:
        """Keyword matching - Confidence: 0.95 if all keywords present"""
        text_lower = utterance.lower()
        
        for intent_type, keywords in self.intent_patterns.items():
            if all(kw.lower() in text_lower for kw in keywords):
                return IntentMatch(
                    intent_type=intent_type,
                    confidence=0.95,
                    entities=entities,
                    source="keyword"
                )
        
        return None


class MLIntentClassifier(IntentClassifier):
    """Neural-based classifier (Padatious style)"""
    confidence_threshold = 0.8
    
    def __init__(self, model=None):
        """In production, load pre-trained model here"""
        self.model = model
    
    def classify(self, utterance: str, entities: Dict[str, str]) -> Optional[IntentMatch]:
        """ML classification - Confidence: 0.5-0.95"""
        if not self.model:
            return None
        
        # In production: actual model inference here
        # For now, simulate with keyword fallback
        confidence, predicted_intent = self.model.predict(utterance)
        
        if confidence >= self.confidence_threshold:
            return IntentMatch(
                intent_type=predicted_intent,
                confidence=confidence,
                entities=entities,
                source="ml_classifier"
            )
        
        return None


# ============================================================================
# 4. CONTEXT MANAGEMENT LAYER (Mycroft ContextManager style)
# ============================================================================

@dataclass
class ContextFrame:
    """Single context frame (entity store)"""
    entities: Dict[str, str]
    timestamp: float
    timeout: int = 2  # seconds
    
    def is_expired(self, current_time: float) -> bool:
        return (current_time - self.timestamp) > self.timeout


class ContextManager:
    """Maintains conversation context frames (Mycroft pattern)"""
    
    def __init__(self, max_frames: int = 3, default_timeout: int = 2):
        self.frame_stack: List[ContextFrame] = []
        self.max_frames = max_frames
        self.default_timeout = default_timeout
    
    def add_frame(self, entities: Dict[str, str], timestamp: float):
        """Add new context frame"""
        frame = ContextFrame(entities, timestamp, self.default_timeout)
        self.frame_stack.append(frame)
        
        # Trim to max frames
        while len(self.frame_stack) > self.max_frames:
            self.frame_stack.pop(0)
    
    def get_current_context(self, timestamp: float) -> Dict[str, str]:
        """Get merged context from all non-expired frames"""
        # Remove expired frames
        self.frame_stack = [
            f for f in self.frame_stack
            if not f.is_expired(timestamp)
        ]
        
        # Merge entities (latest takes precedence)
        merged = {}
        for frame in self.frame_stack:
            merged.update(frame.entities)
        
        return merged


# ============================================================================
# 5. INTENT PARSER WITH PRIORITY MATCHING
# ============================================================================

class IntentParser:
    """Main intent parsing orchestrator (Mycroft IntentService style)"""
    
    def __init__(self):
        self.classifiers: List[tuple[IntentClassifier, float]] = []  # (classifier, weight)
        self.entity_extractors: List[EntityExtractor] = []
        self.context_manager = ContextManager()
    
    def register_classifier(self, classifier: IntentClassifier, priority: int = 0):
        """Register intent classifier with priority"""
        self.classifiers.append((classifier, -priority))  # Negate for sorting
        self.classifiers.sort(key=lambda x: x[1])  # Sort by priority
    
    def register_entity_extractor(self, extractor: EntityExtractor):
        """Register entity extraction method"""
        self.entity_extractors.append(extractor)
    
    def parse(
        self, 
        utterance: str, 
        timestamp: float,
        context: Optional[Dict] = None
    ) -> Optional[IntentMatch]:
        """
        Parse intent using priority-ordered classifiers (Mycroft pattern):
        1. Fast keyword matching (0.95 confidence)
        2. ML classifier (0.5-0.95 confidence)
        3. Context-aware fallback
        """
        
        # Step 1: Extract entities using all methods
        all_entities = {}
        for extractor in self.entity_extractors:
            extracted = extractor.extract(utterance)
            all_entities.update(extracted)
        
        # Step 2: Apply context entities (lower weight than direct extraction)
        context_entities = self.context_manager.get_current_context(timestamp)
        for key, value in context_entities.items():
            if key not in all_entities:
                all_entities[key] = value
        
        # Step 3: Try classifiers in priority order
        best_match: Optional[IntentMatch] = None
        
        for classifier, _ in self.classifiers:
            match = classifier.classify(utterance, all_entities)
            if match:
                best_match = match
                # Continue to try all classifiers, keep best confidence
                # (In production, might break at certain confidence level)
        
        # Step 4: Update context if match found
        if best_match:
            self.context_manager.add_frame(best_match.entities, timestamp)
        
        return best_match


# ============================================================================
# 6. SAFETY VALIDATION LAYER
# ============================================================================

class SafetyLevel(Enum):
    """Safety levels (OpenAssistant pattern: 0-9)"""
    UNRESTRICTED = 0
    NORMAL = 3
    RESTRICTED = 6
    CRITICAL = 9


@dataclass
class SafetyLabel:
    """Safety classification result"""
    label: str  # "__casual__", "__needs_caution__", "__needs_intervention__"
    level: int  # 0-9
    rules_of_thumbs: str  # Guidance for safe response


class SafetyValidator:
    """Safety check and ACL enforcement (Home Assistant + OpenAssistant patterns)"""
    
    def __init__(self):
        self.intent_acl: Dict[IntentType, MatchTargetsConstraints] = {}
        self.safety_labels: Dict[str, SafetyLabel] = {}
    
    def register_intent_acl(self, intent_type: IntentType, constraints: MatchTargetsConstraints):
        """Register ACL for intent (Home Assistant style)"""
        self.intent_acl[intent_type] = constraints
    
    def register_safety_label(self, label_key: str, safety_label: SafetyLabel):
        """Register safety label (OpenAssistant style)"""
        self.safety_labels[label_key] = safety_label
    
    def validate(
        self,
        intent_match: IntentMatch,
        user_safety_level: SafetyLevel,
        target_constraints: Optional[MatchTargetsConstraints] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate intent safety using layered checks:
        1. ACL constraints
        2. Confidence gating
        3. Safety labels
        """
        
        # Check 1: ACL validation
        if intent_match.intent_type in self.intent_acl:
            required_constraints = self.intent_acl[intent_match.intent_type]
            if target_constraints:
                if not self._check_constraints(required_constraints, target_constraints):
                    return False, "ACL constraint failed"
        
        # Check 2: Confidence gating by safety level
        if user_safety_level.value >= SafetyLevel.RESTRICTED.value:
            # High safety: require high confidence
            if intent_match.confidence < 0.95:
                return False, f"Insufficient confidence ({intent_match.confidence}) for safety level {user_safety_level}"
        elif user_safety_level.value >= SafetyLevel.NORMAL.value:
            # Medium safety: require medium confidence
            if intent_match.confidence < 0.80:
                return False, f"Low confidence ({intent_match.confidence}) for this operation"
        
        # Check 3: Safety label check
        if user_safety_level.value >= SafetyLevel.CRITICAL.value:
            # Critical: check for intervention labels
            label = self.safety_labels.get("__needs_intervention__")
            if label and intent_match.context and label.label in str(intent_match.context):
                return False, f"Critical safety label detected: {label.label}"
        
        return True, None
    
    def _check_constraints(
        self,
        required: MatchTargetsConstraints,
        target: MatchTargetsConstraints
    ) -> bool:
        """Check if target matches required constraints"""
        
        # All required constraints must be satisfied
        if required.entity_domains:
            if not target.entity_domains:
                return False
            if not any(d in target.entity_domains for d in required.entity_domains):
                return False
        
        if required.device_features:
            if not target.device_features:
                return False
            if not all(f in target.device_features for f in required.device_features):
                return False
        
        return True


# ============================================================================
# 7. STATE MACHINE LAYER
# ============================================================================

class ConversationMode(Enum):
    """Conversation modes"""
    VOICE = "voice"
    TEXT = "text"
    HYBRID = "hybrid"


class ExecutionState(Enum):
    """Intent execution state (FSM)"""
    IDLE = "idle"
    PARSING = "parsing"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class ConversationStateMachine:
    """State machine for conversation flow (Home Assistant + OpenAssistant patterns)"""
    
    def __init__(self):
        self.state = ExecutionState.IDLE
        self.mode = ConversationMode.TEXT
        self.history: List[Dict[str, Any]] = []
    
    def transition(self, new_state: ExecutionState, reason: str = ""):
        """Log state transition"""
        self.history.append({
            'from_state': self.state,
            'to_state': new_state,
            'reason': reason
        })
        self.state = new_state
    
    def can_transition_to(self, target_state: ExecutionState) -> bool:
        """Validate state transitions"""
        valid_transitions = {
            ExecutionState.IDLE: [ExecutionState.PARSING],
            ExecutionState.PARSING: [ExecutionState.CONFIRMING, ExecutionState.EXECUTING, ExecutionState.ERROR],
            ExecutionState.CONFIRMING: [ExecutionState.EXECUTING, ExecutionState.IDLE, ExecutionState.ERROR],
            ExecutionState.EXECUTING: [ExecutionState.COMPLETED, ExecutionState.ERROR],
            ExecutionState.COMPLETED: [ExecutionState.IDLE],
            ExecutionState.ERROR: [ExecutionState.IDLE],
        }
        
        return target_state in valid_transitions.get(self.state, [])


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Demonstrate the multi-layered intent parsing system"""
    
    # Initialize parser
    parser = IntentParser()
    
    # Register entity extractors
    keyword_extractor = KeywordEntityExtractor()
    keyword_extractor.register_entity("LightName", ["bedroom light", "living room", "kitchen"])
    keyword_extractor.register_entity("Location", ["bedroom", "living room", "kitchen"])
    parser.register_entity_extractor(keyword_extractor)
    
    regex_extractor = RegexEntityExtractor()
    regex_extractor.register_pattern("Level", r"(\d+)%")
    parser.register_entity_extractor(regex_extractor)
    
    # Register intent classifiers with priority
    keyword_classifier = KeywordIntentClassifier()
    keyword_classifier.register_intent(IntentType.TURN_ON, ["turn on", "switch on"])
    parser.register_classifier(keyword_classifier, priority=0)  # Highest priority
    
    # Initialize safety validator
    safety = SafetyValidator()
    
    # Register ACL for TURN_ON
    turn_on_constraints = MatchTargetsConstraints(
        entity_domains=["light", "switch"],
        device_features=["brightness"],
        require_single_target=True
    )
    safety.register_intent_acl(IntentType.TURN_ON, turn_on_constraints)
    
    # Register safety labels
    safety.register_safety_label(
        "__needs_intervention__",
        SafetyLabel(
            label="__needs_intervention__",
            level=9,
            rules_of_thumbs="Requires manual intervention"
        )
    )
    
    # Example: Parse user utterance
    utterance = "turn on the bedroom light"
    timestamp = 1234567890.0
    
    # Step 1: Parse intent
    intent_match = parser.parse(utterance, timestamp)
    
    if intent_match:
        print(f"✓ Intent detected: {intent_match.intent_type}")
        print(f"  Confidence: {intent_match.confidence:.2f}")
        print(f"  Source: {intent_match.source}")
        print(f"  Entities: {intent_match.entities}")
        
        # Step 2: Validate safety
        target_constraints = MatchTargetsConstraints(
            entity_domains=["light"],
            device_features=["brightness"]
        )
        
        is_safe, reason = safety.validate(
            intent_match,
            user_safety_level=SafetyLevel.NORMAL,
            target_constraints=target_constraints
        )
        
        if is_safe:
            print(f"✓ Safety check passed")
            print(f"  Action: EXECUTE")
        else:
            print(f"✗ Safety check failed: {reason}")
        
        # Step 3: Handle confirmation if needed
        if intent_match.requires_confirmation():
            print(f"ℹ Requesting confirmation (confidence: {intent_match.confidence:.2f})")
        elif intent_match.requires_clarification():
            print(f"ℹ Requesting clarification (confidence: {intent_match.confidence:.2f})")
    else:
        print("✗ No intent matched")


if __name__ == "__main__":
    example_usage()
