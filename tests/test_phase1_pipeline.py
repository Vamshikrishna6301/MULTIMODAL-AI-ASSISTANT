import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.fusion_engine import FusionEngine

fusion = FusionEngine()

tests = [
    "open chrome",
    "read screen",
    "next button",
    "activate",
    "what time is it",
    "calculate 5 plus 3",
    "who is einstein",
    "hello",
    "asdasdasd"
]

for t in tests:
    decision = fusion.process_text(t)
    print(t)
    print(decision.to_dict())
    print()