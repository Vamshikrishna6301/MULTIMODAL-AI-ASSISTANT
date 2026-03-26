import unittest
from router.decision_router import DecisionRouter
from core.context_memory import ContextMemory


class TestVisionRouting(unittest.TestCase):

    def setUp(self):
        self.context = ContextMemory()
        self.router = DecisionRouter(self.context)

    def test_vision_action_routed_to_execution(self):

        decision = {
            "status": "APPROVED",
            "action": "VISION",
            "target": "screen",
            "task": "describe"
        }

        response = self.router.route(decision)

        # Since ExecutionEngine doesn't yet support VISION,
        # this should NOT return router-level error
        self.assertNotEqual(response.error_code, "UNSUPPORTED_ACTION_TYPE")


if __name__ == "__main__":
    unittest.main()