import pytest
from core.fusion_engine import FusionEngine


@pytest.fixture
def fusion():
    return FusionEngine()


# -----------------------------------------
# 🔥 Repeated Confirmation Abuse
# -----------------------------------------

def test_multiple_yes_without_pending_action(fusion):
    result = fusion.process_text("yes").to_dict()
    assert result["status"] in ["BLOCKED", "APPROVED"]


def test_confirmation_after_irrelevant_text(fusion):
    fusion.process_text("delete file.txt")
    fusion.process_text("hello there")
    confirm = fusion.process_text("yes").to_dict()
    assert confirm["status"] in ["APPROVED", "CONFIRMED"]


# -----------------------------------------
# 🔥 Rapid Command Switching
# -----------------------------------------

def test_fast_switch_commands(fusion):
    fusion.process_text("open chrome")
    fusion.process_text("shutdown system")
    fusion.process_text("cancel")
    result = fusion.process_text("yes").to_dict()
    assert result["status"] in ["BLOCKED", "APPROVED"]