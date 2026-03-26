from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.intent_schema import Intent, IntentType, Mode


@dataclass
class TaskStep:
    step_id: str
    text: str
    action: str
    intent_type: IntentType
    target: Optional[str]
    parameters: Dict
    risk_level: int
    requires_confirmation: bool
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_source: str = "planner"

    def to_decision(self) -> Dict:
        return {
            "status": "APPROVED",
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
            "text": self.text,
        }


@dataclass
class TaskPlan:
    original_text: str
    steps: List[TaskStep]
    confidence: float
    requires_confirmation: bool = False
    risk_level: int = 0

    def to_parameters(self) -> Dict:
        return {
            "original_text": self.original_text,
            "plan_confidence": self.confidence,
            "steps": [
                {
                    "step_id": step.step_id,
                    "text": step.text,
                    "action": step.action,
                    "intent_type": step.intent_type.name,
                    "target": step.target,
                    "parameters": step.parameters,
                    "risk_level": step.risk_level,
                    "requires_confirmation": step.requires_confirmation,
                    "dependencies": step.dependencies,
                    "confidence": step.confidence,
                    "confidence_source": step.confidence_source,
                }
                for step in self.steps
            ],
        }


class TaskPlanner:
    """
    Decomposes compound requests into sequential executable task steps.
    """

    CONNECTOR_PATTERN = re.compile(
        r"\b(?:and then|then|after that|afterwards|and|next)\b",
        re.IGNORECASE,
    )

    def __init__(self, parser, neural_classifier=None):
        self.parser = parser
        self.neural_classifier = neural_classifier

    def build_plan(self, text: str, current_mode: Mode = Mode.COMMAND) -> Optional[TaskPlan]:
        clauses = self._split_into_clauses(text)
        if len(clauses) < 2:
            return None

        steps: List[TaskStep] = []
        prior_target: Optional[str] = None

        for index, clause in enumerate(clauses, start=1):
            intent = self.parser.parse(clause, current_mode=current_mode)
            if intent.intent_type == IntentType.UNKNOWN and self.neural_classifier:
                prediction = self.neural_classifier.classify(clause)
                if prediction:
                    intent = prediction.to_intent(clause)

            if intent.intent_type == IntentType.UNKNOWN or not intent.action or intent.action == "UNKNOWN":
                return None

            target = intent.target or prior_target
            parameters = dict(intent.parameters or {})
            if target and "target" not in parameters:
                parameters["target"] = target
            if intent.action == "SEARCH" and not target and prior_target:
                target = prior_target
                parameters["target"] = prior_target

            step = TaskStep(
                step_id=f"step_{index}",
                text=clause,
                action=intent.action,
                intent_type=intent.intent_type,
                target=target,
                parameters=parameters,
                risk_level=intent.risk_level,
                requires_confirmation=intent.requires_confirmation,
                dependencies=[steps[-1].step_id] if steps else [],
                confidence=float(intent.confidence),
                confidence_source=intent.confidence_source,
            )
            steps.append(step)
            prior_target = target or prior_target

        if len(steps) < 2:
            return None

        plan_confidence = round(sum(step.confidence for step in steps) / len(steps), 3)
        requires_confirmation = any(step.requires_confirmation for step in steps)
        risk_level = max(step.risk_level for step in steps)

        return TaskPlan(
            original_text=text,
            steps=steps,
            confidence=plan_confidence,
            requires_confirmation=requires_confirmation,
            risk_level=risk_level,
        )

    def _split_into_clauses(self, text: str) -> List[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        parts = self.CONNECTOR_PATTERN.split(normalized)
        clauses = [part.strip(" ,.") for part in parts if part.strip(" ,.")]
        return clauses
