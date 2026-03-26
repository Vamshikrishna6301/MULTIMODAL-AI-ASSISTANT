import pytest
from core.context_memory import ContextMemory
from execution.executor import ExecutionEngine


@pytest.fixture
def execution():
    return ExecutionEngine(ContextMemory())


# -----------------------------------------
# 🔥 Invalid Decision Structures
# -----------------------------------------

def test_execution_with_missing_status(execution):
    decision = {"action": "OPEN_APP"}
    r = execution.execute(decision)
    assert not r.success


def test_execution_with_none(execution):
    r = execution.execute(None)
    assert not r.success


def test_execution_with_invalid_parameters(execution):
    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": "not-a-number"}
    }
    r = execution.execute(decision)
    assert not r.success