import pytest
from core.intent_parser import IntentParser


@pytest.fixture
def parser():
    return IntentParser()


# -----------------------------------------
# 🔥 Unicode / Strange Characters
# -----------------------------------------

def test_unicode_input(parser):
    intent = parser.parse("🚀 open chrome 🔥")
    assert intent.action in ["OPEN_APP", "UNKNOWN"]


def test_mixed_case_symbols(parser):
    intent = parser.parse("ReAd   WHAT is On My SCREEN!!!")
    assert intent.action in ["VISION", "READ_SCREEN"]


# -----------------------------------------
# 🔥 Extremely Long Command
# -----------------------------------------

def test_extremely_long_command(parser):
    text = "open chrome " * 1000
    intent = parser.parse(text)
    assert intent is not None


# -----------------------------------------
# 🔥 Injection-style Inputs
# -----------------------------------------

def test_sql_like_input(parser):
    intent = parser.parse("delete users; drop table system")
    assert intent.action == "FILE_OPERATION"


def test_shell_like_input(parser):
    intent = parser.parse("shutdown && rm -rf /")
    assert intent.action == "SYSTEM_CONTROL"


# -----------------------------------------
# 🔥 Empty Variants
# -----------------------------------------

@pytest.mark.parametrize("input_text", ["", "   ", "\n\n", "\t"])
def test_blank_variants(parser, input_text):
    intent = parser.parse(input_text)
    assert intent.action == "UNKNOWN"