import json
from pathlib import Path

from core.response_model import UnifiedResponse
from execution.execution_logger import ExecutionLogger


def test_execution_logger_writes_trace_metadata(tmp_path):
    log_path = tmp_path / "execution_logs.json"
    logger = ExecutionLogger(log_file=str(log_path))

    response = UnifiedResponse.success_response(
        category="execution",
        spoken_message="Opened chrome.",
        metadata={"confidence": 0.95},
    )

    trace_id = logger.log(
        {"status": "APPROVED", "action": "OPEN_APP", "target": "chrome", "risk_level": 1, "parameters": {}},
        response,
    )

    assert trace_id
    assert log_path.exists()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["trace_id"] == trace_id
    assert entry["action"] == "OPEN_APP"
    assert entry["metadata"]["trace_id"] == trace_id


def test_execution_logger_trace_lookup_returns_entries(tmp_path):
    log_path = tmp_path / "execution_logs.json"
    logger = ExecutionLogger(log_file=str(log_path))

    response = UnifiedResponse.error_response(
        category="execution",
        spoken_message="Typing failed.",
        error_code="TYPE_ERROR",
        metadata={"confidence": 0.7},
    )

    trace_id = logger.log(
        {"status": "APPROVED", "action": "TYPE_TEXT", "target": "hello", "risk_level": 1, "parameters": {"target": "hello"}},
        response,
    )

    trace_entries = logger.get_trace(trace_id)

    assert len(trace_entries) == 1
    assert trace_entries[0]["error_code"] == "TYPE_ERROR"


def test_execution_logger_replay_recent_returns_structured_records(tmp_path):
    log_path = tmp_path / "execution_logs.json"
    logger = ExecutionLogger(log_file=str(log_path))

    response = UnifiedResponse.success_response(
        category="execution",
        spoken_message="Done.",
        metadata={"confidence": 0.88},
    )

    logger.log(
        {"status": "APPROVED", "action": "GET_TIME", "target": "", "risk_level": 0, "parameters": {}},
        response,
    )

    replay = logger.replay_recent(limit=5)

    assert replay
    assert replay[0]["action"] == "GET_TIME"
    assert replay[0]["status"] in {"success", "failed", "blocked"}
