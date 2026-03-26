import random
import string
from core.intent_parser import IntentParser


def random_string(length=50):
    return ''.join(random.choices(string.printable, k=length))


def test_random_fuzz_500():
    parser = IntentParser()
    for _ in range(500):
        text = random_string()
        intent = parser.parse(text)
        assert intent is not None