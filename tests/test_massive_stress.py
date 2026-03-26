import time
from core.intent_parser import IntentParser


def test_10k_parses_under_time():
    parser = IntentParser()
    start = time.time()

    for _ in range(10000):
        parser.parse("open chrome")

    duration = time.time() - start
    assert duration < 2.0  # Adjust based on machine