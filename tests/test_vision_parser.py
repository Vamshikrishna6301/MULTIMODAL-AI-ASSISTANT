import unittest
from core.intent_parser import IntentParser


class TestVisionIntentParsing(unittest.TestCase):

    def setUp(self):
        self.parser = IntentParser()

    def test_read_screen_intent(self):

        intent = self.parser.parse("Read what is on my screen")

        self.assertEqual(intent.action, "VISION")
        self.assertEqual(intent.target, "screen")
        self.assertEqual(intent.parameters.get("task"), "read_text")

    def test_look_screen_intent(self):

        intent = self.parser.parse("Look at the screen")

        self.assertEqual(intent.action, "VISION")
        self.assertEqual(intent.target, "screen")
        self.assertEqual(intent.parameters.get("task"), "describe")

    def test_grounded_click_intent(self):

        intent = self.parser.parse("click red icon")

        self.assertEqual(intent.action, "VISION")
        self.assertEqual(intent.target, "screen")
        self.assertEqual(intent.parameters.get("task"), "click")
        self.assertEqual(intent.parameters.get("query"), "red icon")


if __name__ == "__main__":
    unittest.main()
