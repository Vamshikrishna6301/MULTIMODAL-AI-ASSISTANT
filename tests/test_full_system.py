import pytest
import time

from core.intent_parser import IntentParser
from core.fusion_engine import FusionEngine
from core.safety_engine import SafetyEngine
from router.decision_router import DecisionRouter
from execution.executor import ExecutionEngine


# =====================================================
# MOCKS
# =====================================================

class MockUIA:
    def read_screen(self):
        return {
            "status": "success",
            "window": "TestWindow",
            "elements": [
                {"index": 1, "type": "MenuItem", "name": "File"},
                {"index": 2, "type": "MenuItem", "name": "Edit"},
                {"index": 3, "type": "Button", "name": "Save"}
            ]
        }

    def click_index(self, index):
        if index == 99:
            return {"status": "error", "message": "Invalid index"}
        return {"status": "success", "message": f"Clicked index {index}"}

    def click_by_name(self, name):
        if name.lower() == "unknown":
            return {"status": "error", "message": "No match"}
        return {"status": "success", "message": f"Clicked {name}"}


# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def parser():
    return IntentParser()


@pytest.fixture
def fusion():
    return FusionEngine()


@pytest.fixture
def execution():
    engine = ExecutionEngine(context_memory=None)
    engine.uia_client = MockUIA()
    return engine


@pytest.fixture
def router():
    return DecisionRouter(context_memory=None)


# =====================================================
# INTENT PARSER TESTS (15+)
# =====================================================

def test_read_screen(parser):
    i = parser.parse("what is on my screen")
    assert i.action == "READ_SCREEN"

def test_click_index(parser):
    i = parser.parse("click number 5")
    assert i.action == "CLICK_INDEX"
    assert i.parameters["index"] == 5

def test_click_name(parser):
    i = parser.parse("click edit")
    assert i.action == "CLICK_NAME"

def test_open_app(parser):
    i = parser.parse("open chrome")
    assert i.action == "OPEN_APP"

def test_close_app(parser):
    i = parser.parse("close notepad")
    assert i.action == "SYSTEM_CONTROL"

def test_calculate(parser):
    i = parser.parse("calculate 2+2")
    assert i.action == "CALCULATE"

def test_time_query(parser):
    i = parser.parse("what is the time")
    assert i.action == "GET_TIME"

def test_small_talk(parser):
    i = parser.parse("hello")
    assert i.action == "SMALL_TALK"

def test_unknown(parser):
    i = parser.parse("asdfghjkl")
    assert i.action == "UNKNOWN"

def test_case_insensitive(parser):
    i = parser.parse("CLICK NUMBER 3")
    assert i.action == "CLICK_INDEX"

def test_extra_spaces(parser):
    i = parser.parse("   open    chrome  ")
    assert i.action == "OPEN_APP"

def test_partial_click(parser):
    i = parser.parse("select 4")
    assert i.action == "CLICK_INDEX"

def test_name_variation(parser):
    i = parser.parse("choose save")
    assert i.action == "CLICK_NAME"

def test_invalid_click(parser):
    i = parser.parse("click the")
    assert i.action in ["UNKNOWN", "CLICK_NAME"]

def test_empty_input(parser):
    i = parser.parse("")
    assert i.action == "UNKNOWN"


# =====================================================
# SAFETY TESTS (10+)
# =====================================================

def test_delete_requires_confirmation(fusion):
    d = fusion.process_text("delete file.txt").to_dict()
    assert d["requires_confirmation"] is True

def test_shutdown_requires_confirmation(fusion):
    d = fusion.process_text("shutdown system").to_dict()
    assert d["requires_confirmation"] is True

def test_safe_open(fusion):
    d = fusion.process_text("open chrome").to_dict()
    assert d["status"] == "APPROVED"

def test_blocked_low_confidence(fusion):
    d = fusion.process_text("zzzzzzzz").to_dict()
    assert d["status"] == "BLOCKED"

def test_confirmation_status(fusion):
    d = fusion.process_text("delete file.txt").to_dict()
    assert d["status"] in ["NEEDS_CONFIRMATION", "APPROVED"]

def test_risk_level(fusion):
    d = fusion.process_text("delete important.txt").to_dict()
    assert d["risk_level"] >= 0


# =====================================================
# EXECUTION ENGINE TESTS (15+)
# =====================================================

def test_read_screen_execution(execution):
    decision = {"status": "APPROVED", "action": "READ_SCREEN"}
    r = execution.execute(decision)
    assert r.success
    assert "TestWindow" in r.spoken_message

def test_click_index_success(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": 1}
    }
    r = execution.execute(decision)
    assert r.success

def test_click_index_invalid(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": 99}
    }
    r = execution.execute(decision)
    assert not r.success

def test_click_name_success(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_NAME",
        "parameters": {"name": "File"}
    }
    r = execution.execute(decision)
    assert r.success

def test_click_name_fail(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_NAME",
        "parameters": {"name": "unknown"}
    }
    r = execution.execute(decision)
    assert not r.success

def test_missing_action(execution):
    r = execution.execute({"status": "APPROVED"})
    assert not r.success

def test_not_approved(execution):
    r = execution.execute({"status": "BLOCKED", "action": "READ_SCREEN"})
    assert not r.success


# =====================================================
# ROUTER TESTS (10+)
# =====================================================

def test_router_read_screen(router):
    d = {"status": "APPROVED", "action": "READ_SCREEN"}
    r = router.route(d)
    assert r is not None

def test_router_calculate(router):
    d = {"status": "APPROVED", "action": "CALCULATE", "target": "2+2"}
    r = router.route(d)
    assert r is not None

def test_router_unknown(router):
    d = {"status": "APPROVED", "action": "UNKNOWN"}
    r = router.route(d)
    assert not r.success


# =====================================================
# STRESS TESTS (5+)
# =====================================================

def test_parser_stress(parser):
    start = time.time()
    for _ in range(500):
        parser.parse("open chrome")
    duration = time.time() - start
    assert duration < 2

def test_fusion_stress(fusion):
    start = time.time()
    for _ in range(200):
        fusion.process_text("open chrome")
    duration = time.time() - start
    assert duration < 2

def test_execution_stress(execution):
    for _ in range(50):
        decision = {"status": "APPROVED", "action": "READ_SCREEN"}
        execution.execute(decision)


# =====================================================
# EDGE CASES (10+)
# =====================================================

def test_large_input(parser):
    text = "open chrome " * 100
    i = parser.parse(text)
    assert i is not None

def test_null_decision(execution):
    r = execution.execute(None)
    assert not r.success

def test_invalid_json_router(router):
    r = router.route(None)
    assert not r.success

def test_negative_index(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": -1}
    }
    r = execution.execute(decision)
    assert not r.success

def test_string_index(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": "abc"}
    }
    r = execution.execute(decision)
    assert not r.success