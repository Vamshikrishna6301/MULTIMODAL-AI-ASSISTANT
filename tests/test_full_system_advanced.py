import pytest
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor

from core.intent_parser import IntentParser
from core.fusion_engine import FusionEngine
from core.safety_engine import SafetyEngine
from router.decision_router import DecisionRouter
from execution.executor import ExecutionEngine


# =====================================================
# MOCK UIA
# =====================================================

class MockUIA:
    def read_screen(self):
        return {
            "status": "success",
            "window": "StressTestWindow",
            "elements": [
                {"index": i, "type": "Button", "name": f"Button{i}"}
                for i in range(1, 21)
            ]
        }

    def click_index(self, index):
        if not isinstance(index, int) or index <= 0 or index > 20:
            return {"status": "error", "message": "Invalid index"}
        return {"status": "success", "message": f"Clicked index {index}"}

    def click_by_name(self, name):
        if name.lower().startswith("button"):
            return {"status": "success", "message": f"Clicked {name}"}
        return {"status": "error", "message": "No match"}


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
# END-TO-END PIPELINE TESTS
# =====================================================

def test_full_pipeline_click(parser, fusion, router, execution):
    text = "click button5"
    intent = parser.parse(text)
    decision = fusion.process_text(text).to_dict()
    routed = router.route(decision)
    result = execution.execute(decision)

    assert intent.action in ["CLICK_NAME", "CLICK_INDEX"]
    assert decision["status"] in ["APPROVED", "NEEDS_CONFIRMATION"]
    assert result is not None


def test_full_pipeline_read_screen(parser, fusion, router, execution):
    text = "what is on my screen"
    decision = fusion.process_text(text).to_dict()
    result = execution.execute(decision)
    assert result.success
    assert "StressTestWindow" in result.spoken_message


# =====================================================
# SAFETY ABUSE TESTS
# =====================================================

@pytest.mark.parametrize("command", [
    "delete all files",
    "delete C:\\",
    "format disk",
    "shutdown now",
    "restart system",
])
def test_high_risk_commands_require_confirmation(fusion, command):
    decision = fusion.process_text(command).to_dict()
    assert decision["requires_confirmation"] or decision["status"] == "BLOCKED"


def test_mass_delete_blocked(fusion):
    decision = fusion.process_text("delete everything").to_dict()
    assert decision["risk_level"] >= 5


# =====================================================
# ROUTER VALIDATION
# =====================================================

def test_router_blocks_unapproved(router):
    decision = {"status": "BLOCKED", "action": "CLICK_INDEX"}
    result = router.route(decision)
    assert not result.success


def test_router_invalid_input(router):
    result = router.route("invalid")
    assert not result.success


# =====================================================
# EXECUTION RESILIENCE
# =====================================================

def test_execution_rejects_missing_parameters(execution):
    decision = {"status": "APPROVED", "action": "CLICK_INDEX"}
    result = execution.execute(decision)
    assert not result.success


def test_execution_invalid_type(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": "abc"}
    }
    result = execution.execute(decision)
    assert not result.success


def test_execution_out_of_bounds(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": 999}
    }
    result = execution.execute(decision)
    assert not result.success


# =====================================================
# STRESS TESTING
# =====================================================

def test_parser_massive_stress(parser):
    start = time.time()
    for _ in range(2000):
        parser.parse("open chrome")
    assert time.time() - start < 5


def test_fusion_massive_stress(fusion):
    start = time.time()
    for _ in range(1000):
        fusion.process_text("open chrome")
    assert time.time() - start < 5


def test_execution_stress_parallel(execution):
    decision = {"status": "APPROVED", "action": "READ_SCREEN"}

    def task():
        return execution.execute(decision)

    with ThreadPoolExecutor(max_workers=10) as executor_pool:
        results = list(executor_pool.map(lambda _: task(), range(50)))

    assert all(r.success for r in results)


# =====================================================
# FUZZ TESTING
# =====================================================

def random_string(length=50):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def test_parser_fuzz(parser):
    for _ in range(200):
        text = random_string(100)
        intent = parser.parse(text)
        assert intent is not None


def test_fusion_fuzz(fusion):
    for _ in range(200):
        text = random_string(100)
        decision = fusion.process_text(text)
        assert decision is not None


# =====================================================
# PERFORMANCE BENCHMARKS
# =====================================================

def test_parser_latency(parser):
    start = time.time()
    parser.parse("open chrome")
    latency = time.time() - start
    assert latency < 0.05


def test_fusion_latency(fusion):
    start = time.time()
    fusion.process_text("open chrome")
    latency = time.time() - start
    assert latency < 0.1


# =====================================================
# CONFIRMATION LOOP TEST
# =====================================================

def test_confirmation_flow(fusion):
    decision = fusion.process_text("delete test.txt").to_dict()
    assert decision["requires_confirmation"]

    confirm = fusion.process_text("yes").to_dict()
    assert confirm["status"] in ["APPROVED", "CONFIRMED"]


# =====================================================
# MEMORY CONTEXT TEST
# =====================================================

def test_context_retains_state(fusion):
    fusion.process_text("delete test.txt")
    confirm = fusion.process_text("yes")
    assert confirm is not None


# =====================================================
# EXTREME INPUT TEST
# =====================================================

def test_very_large_input(parser):
    text = "open chrome " * 1000
    intent = parser.parse(text)
    assert intent is not None