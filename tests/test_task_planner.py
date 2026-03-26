from core.fusion_engine import FusionEngine
from core.task_planner import TaskPlanner
from core.response_model import UnifiedResponse
from router.decision_router import DecisionRouter


def test_task_planner_builds_two_step_plan():
    fusion = FusionEngine()
    planner = fusion.task_planner

    plan = planner.build_plan("open chrome and search youtube")

    assert plan is not None
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "OPEN_APP"
    assert plan.steps[1].action == "SEARCH"
    assert plan.steps[1].target == "youtube"


def test_fusion_emits_task_plan_for_compound_command():
    fusion = FusionEngine()

    decision = fusion.process_text("open chrome and search youtube").to_dict()

    assert decision["status"] == "APPROVED"
    assert decision["action"] == "TASK_PLAN"
    assert len(decision["parameters"]["steps"]) == 2


class _FakeExecutionEngine:
    def __init__(self):
        self.calls = []
        self.camera_detector = None

    def execute(self, decision):
        self.calls.append(decision)
        return UnifiedResponse.success_response(
            category="execution",
            spoken_message=f"executed {decision['action']}",
        )


class _FakeVisionQueryEngine:
    def handle(self, decision):
        return UnifiedResponse.success_response(
            category="vision",
            spoken_message="vision ok",
        )


def test_router_executes_planned_steps_sequentially():
    router = DecisionRouter(context_memory=None)
    fake_execution = _FakeExecutionEngine()
    router.execution_engine = fake_execution
    router.vision_query_engine = _FakeVisionQueryEngine()

    plan = FusionEngine().task_planner.build_plan("open chrome and search youtube")

    response = router.route(
        {
            "status": "APPROVED",
            "action": "TASK_PLAN",
            "parameters": plan.to_parameters(),
        }
    )

    assert response.success is True
    assert len(fake_execution.calls) == 2
    assert fake_execution.calls[0]["action"] == "OPEN_APP"
    assert fake_execution.calls[1]["action"] == "SEARCH"
