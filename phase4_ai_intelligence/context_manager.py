"""
Conversation Context & Memory Management
==========================================

Manages conversation history, context, and semantic understanding
across multi-turn interactions.

Features:
- Sliding window context management
- Semantic context compression
- Intent history tracking
- Entity coreference resolution
- Context-aware response generation
- Memory efficiency with cleanup

Context Window Strategies:
- Fixed size: Last N turns
- Semantic: Keep semantically relevant turns
- Hybrid: Combine fixed size with semantic importance
"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class ContextStrategy(str, Enum):
    """Context window management strategies."""
    FIXED_SIZE = "fixed_size"          # Keep last N turns
    SEMANTIC = "semantic"              # Keep semantically important turns
    HYBRID = "hybrid"                  # Combine both


@dataclass
class ConversationTurn:
    """Single turn in conversation."""
    user_input: str
    assistant_response: str
    intent: Optional[str] = None
    entities: List[Dict] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    semantic_importance: float = 0.5   # 0-1 score
    metadata: Dict = field(default_factory=dict)
    
    def age_seconds(self) -> float:
        """Get age of turn in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "user": self.user_input[:100],
            "assistant": self.assistant_response[:100],
            "intent": self.intent,
            "entities_count": len(self.entities),
            "age_seconds": round(self.age_seconds(), 1),
            "importance": round(self.semantic_importance, 2),
        }


@dataclass
class ConversationContext:
    """Complete conversation context."""
    session_id: str
    turns: List[ConversationTurn]
    global_entities: Dict[str, str]  # Coreference resolution
    conversation_goals: List[str]     # Tracked goals
    context_strategy: ContextStrategy
    max_turns: int
    current_turn_index: int = 0
    created_at: float = field(default_factory=time.time)
    
    def get_summary(self) -> str:
        """Get human-readable context summary."""
        parts = [f"Session ID: {self.session_id}"]
        parts.append(f"Turns: {len(self.turns)}")
        
        if self.turns:
            last_turn = self.turns[-1]
            parts.append(f"Last Input: {last_turn.user_input[:50]}...")
            
            if self.global_entities:
                parts.append(f"Entities: {', '.join(self.global_entities.keys())}")
            
            if self.conversation_goals:
                parts.append(f"Goals: {', '.join(self.conversation_goals)}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "turns_count": len(self.turns),
            "strategy": self.context_strategy.value,
            "entities": self.global_entities,
            "goals": self.conversation_goals,
            "age_seconds": round(time.time() - self.created_at, 1),
        }


class ContextManager:
    """
    Production-grade conversation context manager.
    
    Handles multi-turn conversation state, entity coreference,
    and semantic context compression.
    """
    
    def __init__(self, max_history: int = 10, 
                 strategy: ContextStrategy = ContextStrategy.HYBRID,
                 semantic_importance_threshold: float = 0.6):
        """
        Initialize context manager.
        
        Args:
            max_history: Maximum turns to keep
            strategy: Context window strategy
            semantic_importance_threshold: Minimum importance to keep
        """
        self.max_history = max_history
        self.strategy = strategy
        self.importance_threshold = semantic_importance_threshold
        
        self.contexts: Dict[str, ConversationContext] = {}
        self.current_session_id: Optional[str] = None
    
    def create_session(self, session_id: str) -> ConversationContext:
        """
        Create new conversation session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            New ConversationContext
        """
        context = ConversationContext(
            session_id=session_id,
            turns=[],
            global_entities={},
            conversation_goals=[],
            context_strategy=self.strategy,
            max_turns=self.max_history,
        )
        
        self.contexts[session_id] = context
        self.current_session_id = session_id
        
        logger.info(f"Created session: {session_id}")
        
        return context
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get existing session."""
        return self.contexts.get(session_id)
    
    def set_current_session(self, session_id: str) -> bool:
        """Set current active session."""
        if session_id in self.contexts:
            self.current_session_id = session_id
            return True
        return False
    
    def add_turn(self, user_input: str, assistant_response: str,
                 intent: Optional[str] = None,
                 entities: Optional[List[Dict]] = None,
                 metadata: Optional[Dict] = None,
                 importance: float = 0.5) -> bool:
        """
        Add turn to current session.
        
        Args:
            user_input: User message
            assistant_response: Assistant response
            intent: Recognized intent
            entities: Extracted entities
            metadata: Additional metadata
            importance: Semantic importance score (0-1)
            
        Returns:
            Success status
        """
        if not self.current_session_id:
            logger.warning("No active session")
            return False
        
        context = self.contexts.get(self.current_session_id)
        if not context:
            return False
        
        turn = ConversationTurn(
            user_input=user_input,
            assistant_response=assistant_response,
            intent=intent,
            entities=entities or [],
            semantic_importance=importance,
            metadata=metadata or {}
        )
        
        context.turns.append(turn)
        
        # Update global entities (coreference resolution)
        self._update_entities(context, entities or [])
        
        # Manage context window
        self._manage_context_window(context)
        
        context.current_turn_index = len(context.turns) - 1
        
        return True
    
    def _update_entities(self, context: ConversationContext, 
                        entities: List[Dict]):
        """Update global entity references."""
        for entity in entities:
            entity_text = entity.get("text", "")
            entity_type = entity.get("type", "UNKNOWN")
            
            if entity_text:
                # Simple coreference: group by type
                key = f"{entity_type.upper()}"
                context.global_entities[key] = entity_text
    
    def _manage_context_window(self, context: ConversationContext):
        """Manage context window based on strategy."""
        if len(context.turns) <= context.max_turns:
            return
        
        if context.context_strategy == ContextStrategy.FIXED_SIZE:
            # Keep last N turns
            context.turns = context.turns[-context.max_turns:]
        
        elif context.context_strategy == ContextStrategy.SEMANTIC:
            # Keep semantically important turns
            scored_turns = [
                (turn, self._compute_importance(turn))
                for turn in context.turns
            ]
            scored_turns.sort(key=lambda x: x[1], reverse=True)
            
            # Keep top turns
            context.turns = [turn for turn, _ in scored_turns[:context.max_turns]]
            context.turns.sort(key=lambda t: t.timestamp)
        
        elif context.context_strategy == ContextStrategy.HYBRID:
            # Combine: keep recent turns + important turns
            recent_turns = context.turns[-(context.max_turns // 2):]
            older_turns = context.turns[:-(context.max_turns // 2)]
            
            # Score older turns
            scored_older = [
                (turn, self._compute_importance(turn))
                for turn in older_turns
            ]
            scored_older.sort(key=lambda x: x[1], reverse=True)
            
            important_older = [
                turn for turn, score in scored_older
                if score >= self.importance_threshold
            ][:context.max_turns // 4]
            
            context.turns = important_older + recent_turns
            context.turns.sort(key=lambda t: t.timestamp)
    
    def _compute_importance(self, turn: ConversationTurn) -> float:
        """Compute semantic importance of turn."""
        # Factors: explicit score, entity count, goal achievement
        importance = turn.semantic_importance
        
        # Bonus for entity-rich turns
        importance += len(turn.entities) * 0.05
        
        # Discount old turns
        age_days = turn.age_seconds() / (24 * 3600)
        importance *= max(0.5, 1.0 - age_days * 0.1)
        
        return max(0.0, min(1.0, importance))
    
    def add_goal(self, goal: str):
        """Add conversation goal."""
        if self.current_session_id:
            context = self.contexts[self.current_session_id]
            if goal not in context.conversation_goals:
                context.conversation_goals.append(goal)
    
    def complete_goal(self, goal: str):
        """Mark goal as completed."""
        if self.current_session_id:
            context = self.contexts[self.current_session_id]
            if goal in context.conversation_goals:
                context.conversation_goals.remove(goal)
    
    def get_context_str(self, num_turns: int = 5) -> str:
        """
        Get last N turns as formatted context string.
        
        Args:
            num_turns: Number of recent turns
            
        Returns:
            Formatted conversation history
        """
        if not self.current_session_id:
            return ""
        
        context = self.contexts[self.current_session_id]
        recent_turns = context.turns[-num_turns:]
        
        lines = []
        for turn in recent_turns:
            lines.append(f"User: {turn.user_input}")
            lines.append(f"Assistant: {turn.assistant_response}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_context_for_llm(self) -> str:
        """Get formatted context for LLM input."""
        if not self.current_session_id:
            return ""
        
        context = self.contexts[self.current_session_id]
        
        parts = []
        
        # Recent turns
        parts.append("Recent Conversation:")
        parts.append(self.get_context_str(num_turns=3))
        
        # Tracked entities
        if context.global_entities:
            parts.append("Known Entities:")
            for ent_type, ent_value in context.global_entities.items():
                parts.append(f"  {ent_type}: {ent_value}")
        
        # Active goals
        if context.conversation_goals:
            parts.append("Active Goals:")
            for goal in context.conversation_goals:
                parts.append(f"  - {goal}")
        
        return "\n".join(parts)
    
    def end_session(self, session_id: str):
        """End conversation session."""
        if session_id in self.contexts:
            del self.contexts[session_id]
            if self.current_session_id == session_id:
                self.current_session_id = None
            logger.info(f"Ended session: {session_id}")
    
    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        total_turns = sum(len(ctx.turns) for ctx in self.contexts.values())
        total_entities = sum(len(ctx.global_entities) for ctx in self.contexts.values())
        
        return {
            "active_sessions": len(self.contexts),
            "total_turns": total_turns,
            "avg_turns_per_session": round(
                total_turns / len(self.contexts) if self.contexts else 0, 1
            ),
            "total_entities_tracked": total_entities,
            "current_session": self.current_session_id,
        }
