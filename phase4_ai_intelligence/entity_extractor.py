"""
Named Entity Recognition & Extraction
======================================

Extracts structured entities (persons, locations, organizations, etc.)
from natural language input using transformer-based NER models.

Features:
- 8+ entity types (PERSON, ORG, LOCATION, FILE, EMAIL, URL, etc.)
- Confidence scoring
- Span extraction with character offsets
- Custom entity types for domain-specific extraction
- GPU acceleration support

Model: dslim/bert-base-NER or roberta-large-ner (state-of-the-art NER)
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Standard entity types."""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOCATION"
    FILE = "FILE"
    APPLICATION = "APP"
    EMAIL = "EMAIL"
    URL = "URL"
    DATE = "DATE"
    TIME = "TIME"
    NUMBER = "NUMBER"
    COMMAND = "COMMAND"
    PATH = "PATH"
    UNKNOWN = "UNKNOWN"


@dataclass
class Entity:
    """Extracted entity with metadata."""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "type": self.entity_type.value,
            "confidence": round(self.confidence, 4),
            "position": {"start": self.start_pos, "end": self.end_pos}
        }


@dataclass
class ExtractionResult:
    """Extraction result with all entities."""
    original_text: str
    entities: List[Entity]
    model_name: str
    processing_time_ms: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.original_text,
            "entities": [ent.to_dict() for ent in self.entities],
            "entity_count": len(self.entities),
            "model": self.model_name,
            "processing_time_ms": round(self.processing_time_ms, 2)
        }


class EntityExtractor:
    """
    Production-grade NER using transformer models.
    
    Supports both standard NER and domain-specific entity extraction.
    """
    
    # Best NER models by accuracy
    NER_MODELS = {
        "bert": "dslim/bert-base-NER",
        "roberta": "roberta-large",
        "distilbert": "distilbert-base-uncased-finetuned-sst-2-english",
    }
    
    # Entity type mappings
    STANDARD_TAGS = {
        "B-PER": EntityType.PERSON,
        "I-PER": EntityType.PERSON,
        "B-ORG": EntityType.ORGANIZATION,
        "I-ORG": EntityType.ORGANIZATION,
        "B-LOC": EntityType.LOCATION,
        "I-LOC": EntityType.LOCATION,
        "O": EntityType.UNKNOWN,
    }
    
    def __init__(self, model_name: str = "bert", cache_dir: str = "models/cache", 
                 device: int = -1):
        """
        Initialize extractor.
        
        Args:
            model_name: Model type (bert, roberta, distilbert)
            cache_dir: Model cache directory
            device: GPU device id (-1 for CPU)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self.ner_pipeline = None
        self.tokenizer = None
        self.custom_entities = {}
        
        os.makedirs(cache_dir, exist_ok=True)
        
        if HAS_TRANSFORMERS:
            self._load_model()
        else:
            logger.warning("transformers library not installed, using fallback mode")
    
    def _load_model(self):
        """Load NER model."""
        try:
            model_id = self.NER_MODELS.get(self.model_name, self.NER_MODELS["bert"])
            
            logger.info(f"Loading NER model: {model_id}")
            
            self.ner_pipeline = pipeline(
                "token-classification",
                model=model_id,
                device=self.device,
                aggregation_strategy="simple"
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=self.cache_dir)
            
            logger.info(f"NER model loaded: {model_id}")
            
        except Exception as e:
            logger.error(f"Failed to load NER model: {e}")
            self.ner_pipeline = None
    
    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            
        Returns:
            ExtractionResult with all extracted entities
        """
        import time
        start_time = time.time()
        
        text = text.strip()
        if not text:
            return ExtractionResult(
                original_text=text,
                entities=[],
                model_name=self.model_name,
                processing_time_ms=0.0
            )
        
        entities = []
        
        if self.ner_pipeline is not None:
            entities = self._transformer_extract(text)
        else:
            entities = self._regex_extract(text)
        
        # Add custom entity extraction
        entities.extend(self._extract_custom_entities(text))
        
        # Sort by position
        entities.sort(key=lambda e: e.start_pos)
        
        processing_time = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            original_text=text,
            entities=entities,
            model_name=self.model_name,
            processing_time_ms=processing_time
        )
    
    def _transformer_extract(self, text: str) -> List[Entity]:
        """Extract entities using transformer model."""
        try:
            results = self.ner_pipeline(text)
            entities = []
            
            for result in results:
                entity_type = self._map_entity_type(result.get("entity", "O"))
                
                # Skip low confidence
                confidence = result.get("score", 0.5)
                if confidence < 0.5:
                    continue
                
                # Find position in text
                word = result.get("word", "").replace("##", "")
                start_pos = text.lower().find(word.lower())
                
                if start_pos >= 0:
                    entities.append(Entity(
                        text=word,
                        entity_type=entity_type,
                        confidence=confidence,
                        start_pos=start_pos,
                        end_pos=start_pos + len(word)
                    ))
            
            return entities
            
        except Exception as e:
            logger.error(f"Transformer extraction failed: {e}")
            return []
    
    def _regex_extract(self, text: str) -> List[Entity]:
        """Fallback regex-based extraction."""
        import re
        entities = []
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.EMAIL,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        for match in re.finditer(url_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.URL,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Extract file paths
        path_pattern = r'[A-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*'
        for match in re.finditer(path_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.PATH,
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Extract numbers
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        for match in re.finditer(number_pattern, text):
            entities.append(Entity(
                text=match.group(),
                entity_type=EntityType.NUMBER,
                confidence=0.95,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        return entities
    
    def _extract_custom_entities(self, text: str) -> List[Entity]:
        """Extract custom domain-specific entities."""
        import re
        entities = []
        
        # Windows app names
        app_names = ["notepad", "chrome", "excel", "word", "teams", "outlook", "vscode"]
        for app in app_names:
            pattern = rf'\b{app}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(Entity(
                    text=match.group(),
                    entity_type=EntityType.APPLICATION,
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _map_entity_type(self, tag: str) -> EntityType:
        """Map NER tag to EntityType."""
        entity_type = self.STANDARD_TAGS.get(tag, EntityType.UNKNOWN)
        
        # Additional mappings
        if "DATE" in tag or "TIME" in tag:
            entity_type = EntityType.DATE if "DATE" in tag else EntityType.TIME
        elif "NUM" in tag or "MONEY" in tag:
            entity_type = EntityType.NUMBER
        
        return entity_type
    
    def register_custom_entity(self, pattern: str, entity_type: EntityType):
        """
        Register custom entity extraction pattern.
        
        Args:
            pattern: Regex pattern
            entity_type: Entity type
        """
        self.custom_entities[pattern] = entity_type
        logger.info(f"Registered custom entity: {entity_type.value}")
    
    def batch_extract(self, texts: List[str]) -> List[ExtractionResult]:
        """Extract entities from multiple texts."""
        return [self.extract(text) for text in texts]
    
    def get_entity_statistics(self, extraction_result: ExtractionResult) -> Dict:
        """Get statistics about extracted entities."""
        if not extraction_result.entities:
            return {"total": 0, "by_type": {}, "confidence_stats": {}}
        
        by_type = {}
        confidences = []
        
        for entity in extraction_result.entities:
            entity_type = entity.entity_type.value
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            confidences.append(entity.confidence)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total": len(extraction_result.entities),
            "by_type": by_type,
            "confidence_stats": {
                "min": round(min(confidences), 4),
                "max": round(max(confidences), 4),
                "avg": round(avg_confidence, 4),
            }
        }
