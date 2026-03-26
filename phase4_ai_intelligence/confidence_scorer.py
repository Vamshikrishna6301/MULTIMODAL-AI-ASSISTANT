"""
Confidence Scoring & Uncertainty Quantification
================================================

Estimates confidence and uncertainty for safety-critical decisions.

Features:
- Multi-factor confidence scoring
- Uncertainty quantification
- Epistemic & aleatoric uncertainty
- Confidence calibration
- Decision thresholds
- Risk assessment

For safety-first systems: Only execute high-confidence intents.
"""

import logging
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"      # > 0.95
    HIGH = "high"                # 0.8-0.95
    MEDIUM = "medium"            # 0.6-0.8
    LOW = "low"                  # 0.4-0.6
    VERY_LOW = "very_low"        # < 0.4


class RiskLevel(str, Enum):
    """Risk level for safety assessment."""
    SAFE = "safe"                # Can execute without confirmation
    CAUTION = "caution"          # Needs review
    WARNING = "warning"          # Needs confirmation
    CRITICAL = "critical"        # Blocked, needs manual approval


@dataclass
class ConfidenceScore:
    """Confidence scoring result."""
    primary_score: float              # 0-1
    uncertainty: float                # 0-1 (higher = more uncertain)
    epistemic_uncertainty: float       # Model uncertainty
    aleatoric_uncertainty: float       # Data uncertainty
    confidence_level: ConfidenceLevel
    contributing_factors: Dict[str, float]
    recommendations: List[str]
    risk_level: RiskLevel
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "confidence": round(self.primary_score, 4),
            "confidence_level": self.confidence_level.value,
            "uncertainty": round(self.uncertainty, 4),
            "epistemic": round(self.epistemic_uncertainty, 4),
            "aleatoric": round(self.aleatoric_uncertainty, 4),
            "factors": {k: round(v, 3) for k, v in self.contributing_factors.items()},
            "risk": self.risk_level.value,
            "recommendations": self.recommendations,
        }


class ConfidenceScorer:
    """
    Production-grade confidence scorer for safety-critical decisions.
    
    Fused multi-factor scoring with uncertainty quantification.
    """
    
    # Threshold configurations
    EXECUTION_THRESHOLD = 0.75   # Minimum confidence to execute
    CONFIRMATION_THRESHOLD = 0.6  # Confidence requiring user confirmation
    
    def __init__(self, execution_threshold: float = 0.75):
        """
        Initialize scorer.
        
        Args:
            execution_threshold: Minimum confidence for auto-execution
        """
        self.execution_threshold = execution_threshold
        self.calibration_data: List[Tuple[float, bool]] = []
    
    def score_intent(self, 
                    classifier_confidence: float,
                    entity_confidence: float,
                    context_relevance: float,
                    historical_success_rate: float = 0.8,
                    consistency_score: float = 0.8,
                    user_feedback_signal: float = 0.5) -> ConfidenceScore:
        """
        Compute fused confidence score for intent.
        
        Args:
            classifier_confidence: From intent classifier (0-1)
            entity_confidence: Average entity recognition confidence (0-1)
            context_relevance: How relevant to current context (0-1)
            historical_success_rate: Historical success rate for this intent type (0-1)
            consistency_score: Multi-model agreement (0-1)
            user_feedback_signal: User feedback signal if available (0-1)
            
        Returns:
            ConfidenceScore
        """
        # Weighted ensemble
        weights = {
            "classifier": 0.35,
            "entities": 0.15,
            "context": 0.15,
            "history": 0.20,
            "consistency": 0.10,
            "feedback": 0.05,
        }
        
        scores = {
            "classifier": classifier_confidence,
            "entities": entity_confidence,
            "context": context_relevance,
            "history": historical_success_rate,
            "consistency": consistency_score,
            "feedback": user_feedback_signal,
        }
        
        # Weighted sum
        primary_score = sum(
            scores[factor] * weights[factor]
            for factor in weights
        )
        
        # Uncertainty: variance of component scores
        component_scores = list(scores.values())
        mean_score = sum(component_scores) / len(component_scores)
        variance = sum((s - mean_score) ** 2 for s in component_scores) / len(component_scores)
        uncertainty = math.sqrt(variance)  # Standard deviation
        
        # Epistemic uncertainty (model uncertainty)
        # Increases with disagreement between models
        epistemic = 1.0 - consistency_score
        
        # Aleatoric uncertainty (data uncertainty)
        # Combines entity and context uncertainty
        aleatoric = (1.0 - entity_confidence + 1.0 - context_relevance) / 2.0
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(primary_score)
        
        # Get risk level
        risk_level = self._assess_risk(primary_score, uncertainty, epistemic)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            primary_score, uncertainty, scores
        )
        
        return ConfidenceScore(
            primary_score=primary_score,
            uncertainty=uncertainty,
            epistemic_uncertainty=epistemic,
            aleatoric_uncertainty=aleatoric,
            confidence_level=confidence_level,
            contributing_factors=scores,
            recommendations=recommendations,
            risk_level=risk_level
        )
    
    def score_response(self,
                      generation_confidence: float,
                      relevance_to_query: float,
                      safety_score: float,
                      context_enrichment: float = 0.7) -> ConfidenceScore:
        """
        Compute confidence score for generated response.
        
        Args:
            generation_confidence: LLM generation confidence
            relevance_to_query: Response relevance to user query
            safety_score: Safety assessment (0-1, higher = safer)
            context_enrichment: Context provided to LLM (0-1)
            
        Returns:
            ConfidenceScore
        """
        # Response-specific weights
        weights = {
            "generation": 0.35,
            "relevance": 0.30,
            "safety": 0.20,
            "context": 0.15,
        }
        
        scores = {
            "generation": generation_confidence,
            "relevance": relevance_to_query,
            "safety": safety_score,
            "context": context_enrichment,
        }
        
        primary_score = sum(
            scores[factor] * weights[factor]
            for factor in weights
        )
        
        # Uncertainty based on component variance
        component_scores = list(scores.values())
        mean_score = sum(component_scores) / len(component_scores)
        variance = sum((s - mean_score) ** 2 for s in component_scores) / len(component_scores)
        uncertainty = math.sqrt(variance)
        
        epistemic = 1.0 - scores["generation"]
        aleatoric = 1.0 - scores["relevance"]
        
        confidence_level = self._get_confidence_level(primary_score)
        risk_level = self._assess_risk(primary_score, uncertainty, epistemic)
        
        recommendations = []
        if safety_score < 0.6:
            recommendations.append("Low safety score - review response carefully")
        if scores["relevance"] < 0.6:
            recommendations.append("Low relevance - response may not address query")
        if uncertainty > 0.3:
            recommendations.append("High uncertainty - consider alternative approaches")
        
        return ConfidenceScore(
            primary_score=primary_score,
            uncertainty=uncertainty,
            epistemic_uncertainty=epistemic,
            aleatoric_uncertainty=aleatoric,
            confidence_level=confidence_level,
            contributing_factors=scores,
            recommendations=recommendations,
            risk_level=risk_level
        )
    
    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Map score to confidence level."""
        if score >= 0.95:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _assess_risk(self, primary_score: float,
                    uncertainty: float,
                    epistemic: float) -> RiskLevel:
        """Assess risk level for safety."""
        # Combination of low confidence and high uncertainty = high risk
        risk_score = (1.0 - primary_score) + uncertainty + epistemic
        risk_score /= 3.0
        
        if primary_score >= 0.95 and uncertainty < 0.1:
            return RiskLevel.SAFE
        elif primary_score >= 0.8 and uncertainty < 0.2:
            return RiskLevel.CAUTION
        elif primary_score >= 0.6 or uncertainty < 0.3:
            return RiskLevel.WARNING
        else:
            return RiskLevel.CRITICAL
    
    def _generate_recommendations(self, score: float,
                                 uncertainty: float,
                                 factors: Dict[str, float]) -> List[str]:
        """Generate recommendations based on confidence analysis."""
        recommendations = []
        
        if score < 0.6:
            recommendations.append("Low confidence - consider requesting clarification")
        
        if uncertainty > 0.3:
            recommendations.append("High uncertainty - review contributing factors")
        
        # Check lowest scoring factors
        lowest_factor = min(factors.items(), key=lambda x: x[1])
        if lowest_factor[1] < 0.5:
            recommendations.append(f"Low {lowest_factor[0]} - may need improvement")
        
        if score >= self.execution_threshold:
            recommendations.append("✓ Confidence sufficient for execution")
        else:
            recommendations.append("✗ Request user confirmation before execution")
        
        return recommendations
    
    def should_execute(self, score: ConfidenceScore) -> Tuple[bool, str]:
        """
        Determine if action should be executed automatically.
        
        Returns:
            (should_execute, reason)
        """
        if score.primary_score >= self.execution_threshold:
            if score.risk_level == RiskLevel.SAFE:
                return True, "Confidence and safety sufficient for execution"
            else:
                return False, f"Risk level too high: {score.risk_level.value}"
        else:
            return False, f"Confidence {score.primary_score:.2%} below threshold {self.execution_threshold:.2%}"
    
    def calibrate(self, prediction_score: float, actual_outcome: bool):
        """
        Calibrate confidence scorer with feedback.
        
        Args:
            prediction_score: The confidence score given
            actual_outcome: Whether the prediction was correct
        """
        self.calibration_data.append((prediction_score, actual_outcome))
        
        # Keep last 100 calibration samples
        if len(self.calibration_data) > 100:
            self.calibration_data = self.calibration_data[-100:]
    
    def get_calibration_metrics(self) -> Dict:
        """Get calibration metrics."""
        if not self.calibration_data:
            return {"error": "No calibration data"}
        
        # Group by score ranges
        ranges = {
            "0.0-0.2": [], "0.2-0.4": [], "0.4-0.6": [],
            "0.6-0.8": [], "0.8-1.0": []
        }
        
        for score, outcome in self.calibration_data:
            if score < 0.2:
                ranges["0.0-0.2"].append(outcome)
            elif score < 0.4:
                ranges["0.2-0.4"].append(outcome)
            elif score < 0.6:
                ranges["0.4-0.6"].append(outcome)
            elif score < 0.8:
                ranges["0.6-0.8"].append(outcome)
            else:
                ranges["0.8-1.0"].append(outcome)
        
        calibration_metrics = {}
        for range_name, outcomes in ranges.items():
            if outcomes:
                accuracy = sum(outcomes) / len(outcomes)
                calibration_metrics[range_name] = {
                    "samples": len(outcomes),
                    "accuracy": round(accuracy, 3)
                }
        
        return calibration_metrics
