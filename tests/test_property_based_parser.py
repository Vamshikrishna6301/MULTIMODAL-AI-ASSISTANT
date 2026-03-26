from hypothesis import given, strategies as st
from core.intent_parser import IntentParser

parser = IntentParser()

@given(st.text())
def test_parser_never_crashes(random_text):
    intent = parser.parse(random_text)
    assert intent is not None