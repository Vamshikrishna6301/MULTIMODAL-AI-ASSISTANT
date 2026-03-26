"""
Phase 4 AI Intelligence Integration Layer
==========================================

Brings together all AI/ML components for complete Phase 4 integration
with Phase 1-3 system.

Orchestrates:
- Intent classification with confidence scoring
- Entity extraction and coreference resolution
- RAG-based semantic search
- Advanced response generation
- Conversation context management
- Multi-model agnostic decisions

Integration Pattern:
1. User input → Intent Classifier (+ Entity Extractor)
2. Confidence Scorer evaluates decision confidence
3. Context Manager maintains conversation state
4. Semantic Search retrieves relevant knowledge
5. Response Generator creates contextual response
6. Feed back to infrastructure for logging/persistence
"""

import logging
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .intent_classifier import AdvancedIntentClassifier, IntentPrediction, IntentCategory
from .entity_extractor import EntityExtractor, ExtractionResult
from .semantic_search import SemanticSearchEngine, RAGSystem
from .context_manager import ContextManager, ConversationContext
from .response_generator import ResponseGenerator, GeneratedResponse
from .confidence_scorer import ConfidenceScorer, ConfidenceScore, RiskLevel
from .models.model_manager import ModelManager, ModelType

logger = logging.getLogger(__name__)


@dataclass
class Phase4Request:
    """Structured request to Phase 4."""
    user_input: str
    session_id: str
    mode: str = "command"  # command, question, dictation
    metadata: Dict = None


@dataclass
class Phase4Response:
    """Structured response from Phase 4."""
    intent: IntentPrediction
    entities: ExtractionResult
    entities_text: str
    confidence_score: ConfidenceScore
    recommended_action: str
    should_execute: bool
    generated_response: Optional[GeneratedResponse]
    context_info: str
    processing_time_ms: float


class Phase4Engine:
    """
    Complete Phase 4 AI/ML intelligence engine.
    
    Production-grade system for:
    - Multi-model intent classification
    - Named entity recognition
    - Semantic understanding and RAG
    - Conversational context
    - Advanced response generation
    """
    
    def __init__(self, model_priority: str = "accuracy"):
        """
        Initialize Phase 4 engine.
        
        Args:
            model_priority: "accuracy", "speed", or "balanced"
        """
        self.model_priority = model_priority
        self.start_time = time.time()
        
        # Initialize components
        logger.info("Initializing Phase 4 AI Intelligence Engine...")
        
        self.model_manager = ModelManager(cache_dir="models/cache")
        self.intent_classifier = AdvancedIntentClassifier(model_name="distilbert")
        self.entity_extractor = EntityExtractor(model_name="bert")
        self.semantic_search = SemanticSearchEngine(model_name="minilm")
        self.rag_system = RAGSystem(self.semantic_search)
        self.context_manager = ContextManager(max_history=10)
        self.response_generator = ResponseGenerator(model_type="mistral")
        self.confidence_scorer = ConfidenceScorer()
        
        logger.info("Phase 4 Engine ready")
    
    def process(self, request: Phase4Request) -> Phase4Response:
        """
        Process user input through complete Phase 4 pipeline.
        
        Args:
            request: Phase4Request
            
        Returns:
            Phase4Response
        """
        start_time = time.time()
        
        # Step 1: Ensure session exists
        if not self.context_manager.get_session(request.session_id):
            self.context_manager.create_session(request.session_id)
        
        self.context_manager.set_current_session(request.session_id)
        
        logger.info(f"Processing: {request.user_input[:50]}...")
        
        # Step 2: Intent Classification
        intent_pred = self.intent_classifier.classify(request.user_input)
        logger.info(f"Intent: {intent_pred.primary_intent.value} ({intent_pred.confidence:.2%})")
        
        # Step 3: Entity Extraction
        entities_result = self.entity_extractor.extract(request.user_input)
        entities_text = ", ".join([e.text for e in entities_result.entities])
        logger.info(f"Entities: {len(entities_result.entities)} found")
        
        # Step 4: Confidence Scoring
        confidence = self.confidence_scorer.score_intent(
            classifier_confidence=intent_pred.confidence,
            entity_confidence=0.8 if entities_result.entities else 0.7,
            context_relevance=0.75,
            historical_success_rate=0.85,
            consistency_score=0.82,
            user_feedback_signal=0.5
        )
        
        should_execute, reason = self.confidence_scorer.should_execute(confidence)
        logger.info(f"Confidence: {confidence.confidence_level.value} ({confidence.primary_score:.2%}) - {reason}")
        
        # Step 5: Generate context from semantic search
        rag_context = self.rag_system.generate_context(request.user_input, top_k=3)
        
        # Step 6: Generate response
        generated_response = None
        if confidence.primary_score > 0.5:
            system_prompt = f"User Intent: {intent_pred.primary_intent.value}\n" \
                          f"Entities: {entities_text or 'none'}\n" \
                          f"Mode: {request.mode}"
            
            generated_response = self.response_generator.generate(
                prompt=request.user_input,
                context=rag_context,
                system_prompt=system_prompt,
                safety_mode=True
            )
        
        # Step 7: Add to context
        response_text = generated_response.text if generated_response else "Processing..."
        self.context_manager.add_turn(
            user_input=request.user_input,
            assistant_response=response_text,
            intent=intent_pred.primary_intent.value,
            entities=[e.to_dict() for e in entities_result.entities],
            importance=confidence.primary_score
        )
        
        # Step 8: Determine recommended action
        recommended_action = self._determine_action(intent_pred, confidence, entities_result)
        
        processing_time = (time.time() - start_time) * 1000
        
        return Phase4Response(
            intent=intent_pred,
            entities=entities_result,
            entities_text=entities_text,
            confidence_score=confidence,
            recommended_action=recommended_action,
            should_execute=should_execute,
            generated_response=generated_response,
            context_info=self.context_manager.get_context_str(num_turns=2),
            processing_time_ms=processing_time
        )
    
    def _determine_action(self, intent: IntentPrediction, 
                         confidence: ConfidenceScore,
                         entities: ExtractionResult) -> str:
        """Determine recommended action based on analysis."""
        if intent.primary_intent == IntentCategory.UNKNOWN:
            return "CLARIFY: Ask user for clarification"
        
        if confidence.risk_level == RiskLevel.CRITICAL:
            return "BLOCK: Request requires manual approval"
        
        if confidence.risk_level == RiskLevel.WARNING:
            return "CONFIRM: Get user confirmation before execution"
        
        if confidence.risk_level == RiskLevel.CAUTION:
            return "REVIEW: Review action before execution"
        
        return f"EXECUTE: {intent.extracted_action or 'perform action'}"
    
    def get_system_status(self) -> Dict:
        """Get Phase 4 engine status."""
        uptime_seconds = time.time() - self.start_time
        
        return {
            "status": "operational",
            "uptime_seconds": round(uptime_seconds, 1),
            "components": {
                "intent_classifier": "ready",
                "entity_extractor": "ready",
                "semantic_search": "ready",
                "context_manager": "ready",
                "response_generator": "ready",
                "confidence_scorer": "ready",
            },
            "active_sessions": len(self.context_manager.contexts),
            "model_manager": self.model_manager.get_statistics(),
            "semantic_search": self.semantic_search.get_statistics(),
            "context_manager": self.context_manager.get_statistics(),
        }
    
    def shutdown(self):
        """Gracefully shutdown Phase 4 engine."""
        logger.info("Shutting down Phase 4 engine...")
        
        # Cleanup
        self.context_manager.contexts.clear()
        self.semantic_search.clear_index()
        
        logger.info("Phase 4 engine shutdown complete")


# Singleton instances
_engine: Optional[Phase4Engine] = None


def get_phase4_engine(model_priority: str = "accuracy") -> Phase4Engine:
    """Get or create Phase 4 engine singleton."""
    global _engine
    if _engine is None:
        _engine = Phase4Engine(model_priority=model_priority)
    return _engine


def process_user_input(text: str, session_id: str, mode: str = "command") -> Phase4Response:
    """
    Process user input through Phase 4.
    
    Convenience function for basic usage.
    """
    engine = get_phase4_engine()
    request = Phase4Request(
        user_input=text,
        session_id=session_id,
        mode=mode
    )
    return engine.process(request)
