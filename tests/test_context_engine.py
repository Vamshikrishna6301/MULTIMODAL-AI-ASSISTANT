from core.context_memory import ContextMemory
from core.fusion_engine import FusionEngine
from core.intent_schema import Intent, IntentType
from router.decision_router import DecisionRouter
from core.response_model import UnifiedResponse


def test_context_memory_resolves_follow_up_reference():
    memory = ContextMemory()
    first = Intent(intent_type=IntentType.OPEN_APP, text="open chrome", action="OPEN_APP", target="chrome", confidence=0.95)
    memory.update(first)

    follow_up = Intent(intent_type=IntentType.CONTROL, text="close it", action="SYSTEM_CONTROL", target="it", confidence=0.8)
    enriched = memory.enrich(follow_up)

    assert enriched.target == "chrome"
    assert enriched.context["reference_resolved"] is True


def test_fusion_memory_updates_after_successful_command():
    fusion = FusionEngine()
    fusion.process_text("open chrome")

    snapshot = fusion.memory.get_memory_snapshot()

    assert snapshot["last_app"] == "chrome"
    assert snapshot["last_action"] == "OPEN_APP"


class _FakeExecutionEngine:
    def __init__(self):
        self.camera_detector = None

    def execute(self, decision):
        return UnifiedResponse.success_response(
            category="execution",
            spoken_message="done",
        )


class _FakeVisionQueryEngine:
    def handle(self, decision):
        return UnifiedResponse.success_response(category="vision", spoken_message="vision done")


def test_router_records_turns_into_context_memory():
    memory = ContextMemory()
    router = DecisionRouter(memory)
    router.execution_engine = _FakeExecutionEngine()
    router.vision_query_engine = _FakeVisionQueryEngine()

    response = router.route(
        {
            "status": "APPROVED",
            "action": "OPEN_APP",
            "target": "notepad",
            "text": "open notepad",
        }
    )

    assert response.success is True
    turns = memory.get_recent_turns(1)
    assert len(turns) == 1
    assert turns[0].user_text == "open notepad"
    assert turns[0].assistant_text == "done"
