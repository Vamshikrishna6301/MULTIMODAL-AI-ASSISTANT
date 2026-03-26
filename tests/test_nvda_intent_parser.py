from core.intent_parser import IntentParser


def test_intent_parser_maps_what_is_this_to_read_current():
    parser = IntentParser()

    intent = parser.parse("what is this")

    assert intent.action == "READ_CURRENT"
