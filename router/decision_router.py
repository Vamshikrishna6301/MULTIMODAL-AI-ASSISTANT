from core.response_model import UnifiedResponse
from core.intent_schema import IntentType
from execution.executor import ExecutionEngine
from utility.utility_engine import UtilityEngine
from knowledge.llm_engine import LLMEngine
from knowledge.knowledge_engine import KnowledgeEngine
from execution.vision.vision_query_engine import VisionQueryEngine
from core.task_planner import TaskStep


class DecisionRouter:
    """
    Central Routing Engine
    Routes approved decisions to:
    - Execution Engine
    - Utility Engine
    - Knowledge Engine
    - Vision Query Engine
    """

    UTILITY_ACTIONS = {
        "CALCULATE",
        "GET_TIME",
    }

    KNOWLEDGE_ACTIONS = {
        "KNOWLEDGE_QUERY",
    }

    def __init__(self, context_memory):

        self.context_memory = context_memory
        self.execution_engine = ExecutionEngine(context_memory)
        self.utility_engine = UtilityEngine()
        self.llm_engine = LLMEngine(context_memory)
        self.wikipedia_engine = KnowledgeEngine()

        self.vision_query_engine = VisionQueryEngine(
            self.execution_engine.camera_detector
        )

    # =====================================================
    # MAIN ROUTE FUNCTION
    # =====================================================

    def route(self, decision) -> UnifiedResponse:
        print(
            "[PIPELINE] router.route start:",
            {
                "action": decision.get("action") if isinstance(decision, dict) else None,
                "status": decision.get("status") if isinstance(decision, dict) else None,
            },
        )

        # 🔥 Defensive type checking
        if not isinstance(decision, dict):
            return UnifiedResponse.error_response(
                category="router",
                spoken_message="Invalid decision format.",
                error_code="INVALID_DECISION_TYPE"
            )

        if not decision:
            return UnifiedResponse.error_response(
                category="router",
                spoken_message="No decision received.",
                error_code="NO_DECISION"
            )

        if decision.get("status") != "APPROVED":
            return UnifiedResponse.error_response(
                category="router",
                spoken_message="The action was not approved.",
                error_code="ACTION_NOT_APPROVED"
            )

        action = decision.get("action")

        if action == "TASK_PLAN":
            return self._execute_task_plan(decision)

        # --------------------------------------------------
        # VISION QUERY (separate from UIA screen reading)
        # --------------------------------------------------

        if action == "VISION_QUERY":
            response = self.vision_query_engine.handle(decision)
            self._record_turn(decision, response)
            return response

        # --------------------------------------------------
        # UTILITY ACTIONS
        # --------------------------------------------------

        if action in self.UTILITY_ACTIONS:
            response = self.utility_engine.handle(decision)
            self._record_turn(decision, response)
            return response

        # --------------------------------------------------
        # KNOWLEDGE ACTIONS
        # --------------------------------------------------

        if action in self.KNOWLEDGE_ACTIONS:

            query = decision.get("target", "")

            if isinstance(query, str) and query.lower().startswith(("who is", "who was")):
                response = self.wikipedia_engine.handle(decision)
                self._record_turn(decision, response)
                return response

            response = self.llm_engine.handle(decision)
            self._record_turn(decision, response)
            return response

        # --------------------------------------------------
        # EVERYTHING ELSE → EXECUTION ENGINE
        # --------------------------------------------------

        response = self.execution_engine.execute(decision)
        print(
            "[PIPELINE] router.route finish:",
            {
                "action": action,
                "success": getattr(response, "success", False),
                "spoken_message": getattr(response, "spoken_message", None),
            },
        )
        self._record_turn(decision, response)
        return response

    def _execute_task_plan(self, decision) -> UnifiedResponse:

        parameters = decision.get("parameters", {}) or {}
        step_payloads = parameters.get("steps", [])

        if not step_payloads:
            return UnifiedResponse.error_response(
                category="planner",
                spoken_message="The task plan did not contain any executable steps.",
                error_code="EMPTY_TASK_PLAN"
            )

        step_results = []
        last_response = None

        for step_payload in step_payloads:
            step = TaskStep(
                step_id=step_payload.get("step_id"),
                text=step_payload.get("text", ""),
                action=step_payload.get("action"),
                intent_type=IntentType[step_payload.get("intent_type", "CONTROL")],
                target=step_payload.get("target"),
                parameters=step_payload.get("parameters") or {},
                risk_level=step_payload.get("risk_level", 0),
                requires_confirmation=step_payload.get("requires_confirmation", False),
                dependencies=step_payload.get("dependencies") or [],
                confidence=step_payload.get("confidence", 0.0),
                confidence_source=step_payload.get("confidence_source", "task_planner"),
            )

            step_decision = step.to_decision()
            last_response = self.route(step_decision)

            step_results.append(
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "target": step.target,
                    "success": bool(getattr(last_response, "success", False)),
                    "error_code": getattr(last_response, "error_code", None),
                    "spoken_message": getattr(last_response, "spoken_message", None),
                }
            )

            if not getattr(last_response, "success", False):
                return UnifiedResponse.error_response(
                    category="planner",
                    spoken_message=f"Task stopped at {step.step_id}: {last_response.spoken_message}",
                    error_code="TASK_STEP_FAILED",
                    technical_message=getattr(last_response, "technical_message", None),
                    metadata={"step_results": step_results, "failed_step": step.step_id},
                )

        return UnifiedResponse.success_response(
            category="planner",
            spoken_message=last_response.spoken_message if last_response else "Task completed.",
            metadata={"step_results": step_results, "step_count": len(step_results)},
        )

    def _record_turn(self, decision, response):

        if not self.context_memory:
            return

        try:
            user_text = decision.get("text") or decision.get("target") or decision.get("action") or ""
            self.context_memory.record_turn(
                user_text=user_text,
                assistant_text=getattr(response, "spoken_message", "") or "",
                action=decision.get("action"),
                target=decision.get("target"),
                metadata={
                    "success": getattr(response, "success", False),
                    "error_code": getattr(response, "error_code", None),
                    "category": getattr(response, "category", None),
                },
            )
        except Exception:
            pass
