from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.intent_schema import Intent, IntentType, Mode

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np

    MODEL_AVAILABLE = True
except Exception:
    MODEL_AVAILABLE = False
    SentenceTransformer = None
    faiss = None
    np = None


@dataclass(frozen=True)
class IntentDefinition:
    action: str
    intent_type: IntentType
    examples: List[str]
    risk_level: int = 0
    requires_confirmation: bool = False
    target_extractor: Optional[Callable[[str], Optional[str]]] = None
    parameters_extractor: Optional[Callable[[str], Dict[str, str]]] = None


@dataclass
class NeuralIntentPrediction:
    action: str
    intent_type: IntentType
    confidence: float
    confidence_source: str
    target: Optional[str]
    parameters: Dict[str, str]
    risk_level: int
    requires_confirmation: bool
    matched_example: Optional[str] = None

    def to_intent(self, text: str) -> Intent:
        return Intent(
            intent_type=self.intent_type,
            text=text,
            action=self.action,
            target=self.target,
            parameters=self.parameters,
            confidence=self.confidence,
            confidence_source=self.confidence_source,
            risk_level=self.risk_level,
            requires_confirmation=self.requires_confirmation,
            mode=Mode.COMMAND,
        )


def _extract_after_keywords(text: str, keywords: List[str]) -> Optional[str]:
    normalized = text.lower().strip()
    for keyword in keywords:
        if normalized.startswith(keyword + " "):
            value = normalized[len(keyword) :].strip()
            return value or None
    return None


def _extract_search_parameters(text: str) -> Dict[str, str]:
    query = _extract_after_keywords(text, ["search", "find", "look up"])
    return {"query": query} if query else {}


class NeuralIntentClassifier:
    """
    Structured neural intent classifier with graceful fallback mode.
    """

    CONFIDENCE_THRESHOLD = 0.68
    FALLBACK_THRESHOLD = 0.58
    MODEL_NAME = "all-MiniLM-L6-v2"
    LOCAL_MODEL_DIR = Path("models") / "sentence_transformers" / "all-MiniLM-L6-v2"

    def __init__(self):
        self.model = None
        self.index = None
        self.embedding_matrix = None
        self.labels: List[str] = []
        self.examples: List[str] = []
        self.definitions = self._build_definitions()
        self.definition_map = {definition.action: definition for definition in self.definitions}
        self._initialization_error: Optional[str] = None

        if MODEL_AVAILABLE:
            try:
                print("Loading Neural Intent Classifier...")
                model_source = str(self.LOCAL_MODEL_DIR) if self.LOCAL_MODEL_DIR.exists() else None
                if model_source:
                    self.model = SentenceTransformer(model_source)
                else:
                    self._initialization_error = "local sentence-transformer model unavailable"
                    print("Neural intent model unavailable locally, using lexical fallback")
                    self.model = None
                    self.index = None
                    self.embedding_matrix = None
                    return
                self._build_index()
                print("Neural Intent Classifier ready")
            except Exception as exc:
                self._initialization_error = str(exc)
                self.model = None
                self.index = None
                self.embedding_matrix = None
                print(f"Neural intent model unavailable, using lexical fallback: {exc}")
        else:
            self._initialization_error = "sentence-transformers/faiss unavailable"
            print("Neural intent model unavailable, using lexical fallback")

    def status(self) -> Dict[str, Optional[str]]:
        return {
            "model_available": bool(self.model),
            "fallback_available": True,
            "initialization_error": self._initialization_error,
        }

    def classify(self, text: str) -> Optional[NeuralIntentPrediction]:
        normalized = self._normalize(text)
        if not normalized:
            return None

        if self.model and self.index is not None:
            prediction = self._classify_with_embeddings(normalized)
            if prediction and prediction.confidence >= self.CONFIDENCE_THRESHOLD:
                return prediction

        prediction = self._classify_with_lexical_fallback(normalized)
        if prediction and prediction.confidence >= self.FALLBACK_THRESHOLD:
            return prediction

        return None

    def _build_index(self):
        self.examples = []
        self.labels = []

        for definition in self.definitions:
            for example in definition.examples:
                self.examples.append(example)
                self.labels.append(definition.action)

        embeddings = self.model.encode(
            self.examples,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        dimension = embeddings.shape[1]
        self.embedding_matrix = embeddings.astype("float32")
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embedding_matrix)

    def _classify_with_embeddings(self, text: str) -> Optional[NeuralIntentPrediction]:
        embedding = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, ids = self.index.search(embedding, k=min(3, len(self.examples)))
        top_score = float(scores[0][0])
        top_id = int(ids[0][0])
        second_score = float(scores[0][1]) if scores.shape[1] > 1 else 0.0
        margin = max(0.0, top_score - second_score)
        action = self.labels[top_id]
        definition = self.definition_map[action]
        target = self._extract_target(text, definition)
        parameters = self._extract_parameters(text, definition)

        confidence = min(0.99, max(0.0, (top_score * 0.8) + (margin * 0.2)))
        if target:
            confidence = min(0.99, confidence + 0.03)

        return NeuralIntentPrediction(
            action=definition.action,
            intent_type=definition.intent_type,
            confidence=round(confidence, 3),
            confidence_source="neural_embedding",
            target=target,
            parameters=parameters,
            risk_level=definition.risk_level,
            requires_confirmation=definition.requires_confirmation,
            matched_example=self.examples[top_id],
        )

    def _classify_with_lexical_fallback(self, text: str) -> Optional[NeuralIntentPrediction]:
        tokens = set(text.split())
        best_definition = None
        best_score = 0.0
        best_example = None

        for definition in self.definitions:
            for example in definition.examples:
                example_tokens = set(example.split())
                overlap = len(tokens & example_tokens)
                if not example_tokens:
                    continue
                coverage = overlap / len(example_tokens)
                precision = overlap / max(1, len(tokens))
                score = (coverage * 0.7) + (precision * 0.3)

                if score > best_score:
                    best_score = score
                    best_definition = definition
                    best_example = example

        if best_definition is None:
            return None

        target = self._extract_target(text, best_definition)
        parameters = self._extract_parameters(text, best_definition)
        confidence = best_score
        if target:
            confidence += 0.05

        return NeuralIntentPrediction(
            action=best_definition.action,
            intent_type=best_definition.intent_type,
            confidence=round(min(0.92, confidence), 3),
            confidence_source="neural_lexical_fallback",
            target=target,
            parameters=parameters,
            risk_level=best_definition.risk_level,
            requires_confirmation=best_definition.requires_confirmation,
            matched_example=best_example,
        )

    def _extract_target(self, text: str, definition: IntentDefinition) -> Optional[str]:
        if definition.target_extractor:
            return definition.target_extractor(text)
        return None

    def _extract_parameters(self, text: str, definition: IntentDefinition) -> Dict[str, str]:
        if definition.parameters_extractor:
            return definition.parameters_extractor(text)
        return {"target": self._extract_target(text, definition)} if self._extract_target(text, definition) else {}

    def _build_definitions(self) -> List[IntentDefinition]:
        return [
            IntentDefinition(
                action="OPEN_APP",
                intent_type=IntentType.OPEN_APP,
                examples=[
                    "launch chrome browser",
                    "start notepad",
                    "open firefox",
                    "open calculator app",
                ],
                target_extractor=lambda text: _extract_after_keywords(text, ["open", "launch", "start", "run"]),
            ),
            IntentDefinition(
                action="SEARCH",
                intent_type=IntentType.SEARCH,
                examples=[
                    "search for weather",
                    "find cat videos online",
                    "look up python tutorials",
                    "search youtube for music",
                ],
                target_extractor=lambda text: _extract_after_keywords(text, ["search", "find", "look up"]),
                parameters_extractor=_extract_search_parameters,
            ),
            IntentDefinition(
                action="TYPE_TEXT",
                intent_type=IntentType.TYPE_TEXT,
                examples=[
                    "type hello world",
                    "write this sentence",
                    "enter my email address",
                ],
                target_extractor=lambda text: _extract_after_keywords(text, ["type", "write", "enter"]),
            ),
            IntentDefinition(
                action="READ_SCREEN",
                intent_type=IntentType.CONTROL,
                examples=[
                    "what is on my screen",
                    "read the current screen",
                    "describe what you see",
                    "tell me what is visible",
                ],
            ),
            IntentDefinition(
                action="READ_CURRENT",
                intent_type=IntentType.CONTROL,
                examples=[
                    "what is this",
                    "read the focused item",
                    "what is focused right now",
                    "tell me the current element",
                    "read the current line",
                ],
            ),
            IntentDefinition(
                action="NEXT_ITEM",
                intent_type=IntentType.CONTROL,
                examples=[
                    "go to the next item",
                    "move forward in the interface",
                    "next element please",
                ],
            ),
            IntentDefinition(
                action="PREVIOUS_ITEM",
                intent_type=IntentType.CONTROL,
                examples=[
                    "go to the previous item",
                    "move back in the interface",
                    "previous element please",
                ],
            ),
            IntentDefinition(
                action="NEXT_BUTTON",
                intent_type=IntentType.CONTROL,
                examples=[
                    "jump to the next button",
                    "find the next button",
                    "next clickable button",
                ],
            ),
            IntentDefinition(
                action="NEXT_INPUT",
                intent_type=IntentType.CONTROL,
                examples=[
                    "go to the next input field",
                    "find the next textbox",
                    "focus the next text field",
                ],
            ),
            IntentDefinition(
                action="NEXT_LINK",
                intent_type=IntentType.CONTROL,
                examples=[
                    "go to the next link",
                    "find the next hyperlink",
                    "move to the next web link",
                ],
            ),
            IntentDefinition(
                action="GET_TIME",
                intent_type=IntentType.QUESTION,
                examples=[
                    "tell me the time",
                    "what time is it right now",
                    "current time please",
                ],
            ),
            IntentDefinition(
                action="SYSTEM_CONTROL",
                intent_type=IntentType.SYSTEM_CONTROL,
                examples=[
                    "shutdown the computer",
                    "restart the system",
                    "turn off this machine",
                ],
                risk_level=9,
                requires_confirmation=True,
                target_extractor=lambda text: "shutdown" if "shutdown" in text or "turn off" in text else "restart",
            ),
        ]

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
