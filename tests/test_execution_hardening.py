from core.response_model import UnifiedResponse
from execution.execution_hardening import ExecutionHardeningManager


def test_hardening_retries_retryable_response_and_recovers():
    manager = ExecutionHardeningManager()
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] == 1:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="temporary failure",
                error_code="TYPE_ERROR",
            )
        return UnifiedResponse.success_response(
            category="execution",
            spoken_message="typed",
        )

    result = manager.execute("TYPE_TEXT", operation)

    assert result.response.success is True
    assert calls["count"] == 2
    assert result.response.metadata["attempt_count"] == 2


def test_hardening_attempts_rollback_after_failed_retries():
    manager = ExecutionHardeningManager()
    rollback = {"called": 0}

    def operation():
        return UnifiedResponse.error_response(
            category="execution",
            spoken_message="open failed",
            error_code="APP_OPEN_FAILED",
        )

    def rollback_fn():
        rollback["called"] += 1
        return True

    result = manager.execute("OPEN_APP", operation, rollback=rollback_fn)

    assert result.response.success is False
    assert rollback["called"] == 1
    assert result.response.metadata["rollback_attempted"] is True
    assert result.response.metadata["rollback_succeeded"] is True


def test_hardening_wraps_exceptions_into_execution_response():
    manager = ExecutionHardeningManager()

    def operation():
        raise RuntimeError("adapter crashed")

    result = manager.execute("SEARCH", operation)

    assert result.response.success is False
    assert result.response.error_code == "EXECUTION_EXCEPTION"
    assert result.response.metadata["attempt_count"] >= 1
