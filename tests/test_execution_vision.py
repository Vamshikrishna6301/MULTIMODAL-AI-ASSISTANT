import unittest
from core.context_memory import ContextMemory
from execution.executor import ExecutionEngine


class TestVisionExecution(unittest.TestCase):

    def setUp(self):
        self.context = ContextMemory()
        self.engine = ExecutionEngine(self.context)

    # ---------------------------------
    # SCREEN CAPTURE TEST
    # ---------------------------------
    def test_vision_screen_capture(self):

        decision = {
            "status": "APPROVED",
            "action": "VISION",
            "target": "screen",
            "task": "describe",
            "risk_level": 0,
            "requires_confirmation": False,
            "confirmed": False
        }

        response = self.engine.execute(decision)

        self.assertTrue(response.success)
        self.assertEqual(response.category, "execution")
        self.assertIn("Screen captured", response.spoken_message)

    # ---------------------------------
    # OCR TEST
    # ---------------------------------
    def test_vision_read_text(self):

        decision = {
            "status": "APPROVED",
            "action": "VISION",
            "target": "screen",
            "task": "read_text",
            "risk_level": 0,
            "requires_confirmation": False,
            "confirmed": False
        }

        response = self.engine.execute(decision)

        self.assertTrue(response.success)
        self.assertEqual(response.category, "execution")
        # We don't assert exact text because screen content varies


if __name__ == "__main__":
    unittest.main()