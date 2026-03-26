"""
Phase 4: Advanced AI/ML Intelligence Layer
==========================================

Industry-standard production-grade AI/ML components for:
- Advanced intent classification (transformer-based)
- Named entity recognition and extraction
- Semantic search with RAG
- Conversation context management
- Advanced response generation
- Confidence scoring and uncertainty quantification

Key Features:
- State-of-the-art transformer models (DistilBERT, sentence-transformers)
- Production-optimized inference
- Model quantization and caching
- Comprehensive error handling
- Full observability with structured logging
- Safety-first confidence scoring
"""

from .intent_classifier import AdvancedIntentClassifier, IntentPrediction, IntentCategory
from .entity_extractor import EntityExtractor, Entity, EntityType
from .semantic_search import SemanticSearchEngine, SearchResult, RAGSystem
from .context_manager import ConversationContext, ContextManager, ContextStrategy, ConversationTurn
from .response_generator import ResponseGenerator, GeneratedResponse, LLMProvider
from .confidence_scorer import ConfidenceScorer, ConfidenceScore, ConfidenceLevel, RiskLevel
from .models.model_manager import ModelManager, ModelType, QuantizationType, ModelInfo
from .integration import Phase4Engine, Phase4Request, Phase4Response, get_phase4_engine, process_user_input

__version__ = "1.0.0"
__all__ = [
    # Intent Classification
    "AdvancedIntentClassifier",
    "IntentPrediction",
    "IntentCategory",
    
    # Entity Extraction
    "EntityExtractor",
    "Entity",
    "EntityType",
    
    # Semantic Search & RAG
    "SemanticSearchEngine",
    "SearchResult",
    "RAGSystem",
    
    # Context Management
    "ConversationContext",
    "ContextManager",
    "ContextStrategy",
    "ConversationTurn",
    
    # Response Generation
    "ResponseGenerator",
    "GeneratedResponse",
    "LLMProvider",
    
    # Confidence Scoring
    "ConfidenceScorer",
    "ConfidenceScore",
    "ConfidenceLevel",
    "RiskLevel",
    
    # Model Management
    "ModelManager",
    "ModelType",
    "QuantizationType",
    "ModelInfo",
    
    # Integration
    "Phase4Engine",
    "Phase4Request",
    "Phase4Response",
    "get_phase4_engine",
    "process_user_input",
]


def get_intent_classifier(cache_dir: str = "models/cache") -> AdvancedIntentClassifier:
    """Get singleton instance of advanced intent classifier."""
    return AdvancedIntentClassifier(cache_dir=cache_dir)


def get_entity_extractor(cache_dir: str = "models/cache") -> EntityExtractor:
    """Get singleton instance of entity extractor."""
    return EntityExtractor(cache_dir=cache_dir)


def get_semantic_search_engine(cache_dir: str = "models/cache") -> SemanticSearchEngine:
    """Get singleton instance of semantic search engine."""
    return SemanticSearchEngine(cache_dir=cache_dir)


def get_context_manager(max_history: int = 10) -> ContextManager:
    """Get singleton instance of context manager."""
    return ContextManager(max_history=max_history)


def get_response_generator(model_type: str = "mistral") -> ResponseGenerator:
    """Get singleton instance of response generator."""
    return ResponseGenerator(model_type=model_type)


def get_confidence_scorer() -> ConfidenceScorer:
    """Get singleton instance of confidence scorer."""
    return ConfidenceScorer()

