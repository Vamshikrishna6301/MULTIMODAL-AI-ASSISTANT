from core.fusion_engine import FusionEngine
from core.intent_schema import IntentType
from core.neural_intent_classifier import NeuralIntentClassifier


def test_classifier_predicts_open_app_with_target():
    classifier = NeuralIntentClassifier()

    prediction = classifier.classify("launch chrome browser")

    assert prediction is not None
    assert prediction.action == "OPEN_APP"
    assert prediction.intent_type == IntentType.OPEN_APP
    assert "chrome" in (prediction.target or "")
    assert prediction.confidence >= 0.58


def test_classifier_predicts_read_screen_navigation_action():
    classifier = NeuralIntentClassifier()

    prediction = classifier.classify("tell me what is visible")

    assert prediction is not None
    assert prediction.action == "READ_SCREEN"
    assert prediction.intent_type == IntentType.CONTROL


def test_fusion_uses_neural_prediction_for_unknown_phrase():
    fusion = FusionEngine()

    decision = fusion.process_text("tell me what is visible").to_dict()

    assert decision["status"] == "APPROVED"
    assert decision["action"] == "READ_SCREEN"


def test_classifier_marks_shutdown_as_confirmation_required():
    classifier = NeuralIntentClassifier()

    prediction = classifier.classify("turn off this machine")

    assert prediction is not None
    assert prediction.action == "SYSTEM_CONTROL"
    assert prediction.requires_confirmation is True
    assert prediction.risk_level >= 7
