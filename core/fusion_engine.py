import time
from typing import Dict

from .context_memory import ContextMemory
from .intent_parser import IntentParser
from .intent_schema import Intent, IntentType, Mode
from .mode_manager import ModeManager
from .safety_engine import SafetyEngine
from core.neural_intent_classifier import NeuralIntentClassifier
from core.task_planner import TaskPlanner


class Decision:

    def __init__(self, status, intent=None, message=None, latency=None):
        self.status = status
        self.intent = intent
        self.message = message
        self.latency = latency

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "action": self.intent.action if self.intent else None,
            "target": self.intent.target if self.intent else None,
            "parameters": self.intent.parameters if self.intent else {},
            "risk_level": self.intent.risk_level if self.intent else None,
            "requires_confirmation": self.intent.requires_confirmation if self.intent else None,
            "confirmed": getattr(self.intent, "confirmed", False),
            "blocked_reason": self.intent.blocked_reason if self.intent else None,
            "message": self.message,
            "latency_ms": round(self.latency * 1000, 2) if self.latency else None,
        }


class FusionEngine:

    def __init__(self):
        self.parser = IntentParser()
        self.mode_manager = ModeManager()
        self.memory = ContextMemory()
        self.safety = SafetyEngine()
        self.neural_classifier = NeuralIntentClassifier()
        self.task_planner = TaskPlanner(self.parser, self.neural_classifier)

        self.intent_confidence_threshold = 0.4

    # =====================================================

    def process_text(self, text: str) -> Decision:

        start_time = time.time()

        plan = self.task_planner.build_plan(
            text,
            current_mode=self.mode_manager.get_mode()
        )

        if plan:
            intent = Intent(
                intent_type=IntentType.CONTROL,
                text=text,
                action="TASK_PLAN",
                parameters=plan.to_parameters(),
                confidence=plan.confidence,
                confidence_source="task_planner",
                risk_level=plan.risk_level,
                requires_confirmation=plan.requires_confirmation,
            )

            if intent.requires_confirmation:
                return self._finalize(
                    Decision(
                        "NEEDS_CONFIRMATION",
                        intent,
                        "Confirm multi-step task execution"
                    ),
                    start_time
                )

            return self._finalize(
                Decision("APPROVED", intent, "Task plan created"),
                start_time
            )

        intent = self.parser.parse(
            text,
            current_mode=self.mode_manager.get_mode()
        )

        intent = self.mode_manager.handle_intent(intent)

        if intent is None:
            return self._finalize(
                Decision("WAITING_CONFIRMATION", None, "Waiting for confirmation"),
                start_time
            )

        if intent.intent_type == IntentType.CONTROL:
            self._handle_mode_control(intent)

        intent = self.memory.enrich(intent)
        intent = self.safety.evaluate(intent, self.mode_manager.get_mode())

        dangerous_words = ["shutdown", "restart", "delete", "format", "factory reset"]
        if intent.action == "SYSTEM_CONTROL" and intent.target:
            intent.requires_confirmation = False
        elif intent.action == "SYSTEM_CONTROL":
            if any(word in intent.text.lower() for word in dangerous_words):
                intent.requires_confirmation = True
            else:
                intent.requires_confirmation = False

        if intent.blocked_reason:
            return self._finalize(
                Decision("BLOCKED", intent, intent.blocked_reason),
                start_time
            )

        if intent.intent_type == IntentType.UNKNOWN:

            try:
                prediction = self.neural_classifier.classify(text)

                if prediction:
                    intent = prediction.to_intent(text)

                    return self._finalize(
                        Decision("APPROVED", intent, "Neural intent recognized"),
                        start_time
                    )

            except Exception:
                pass

            return self._finalize(
                Decision("BLOCKED", intent, "I did not understand that."),
                start_time
            )

        if intent.requires_confirmation:
            return self._finalize(
                Decision(
                    "NEEDS_CONFIRMATION",
                    intent,
                    f"Confirm action: {intent.action} {intent.target}"
                ),
                start_time
            )

        self.memory.update(intent)

        return self._finalize(
            Decision("APPROVED", intent, "Action approved"),
            start_time
        )

    # =====================================================

    def _handle_mode_control(self, intent: Intent):
        text = intent.text.lower().strip()

        if text == "enter dictation":
            self.mode_manager.set_mode(Mode.DICTATION, "dictation_mode_enabled")
        elif text == "exit dictation":
            self.mode_manager.set_mode(Mode.COMMAND, "exit_dictation")
        elif text == "disable assistant":
            self.mode_manager.set_mode(Mode.DISABLED, "disable_command")
        elif text == "enable assistant":
            self.mode_manager.set_mode(Mode.LISTENING, "enable_assistant")

    # =====================================================

    def _finalize(self, decision: Decision, start_time: float) -> Decision:
        decision.latency = time.time() - start_time
        return decision
