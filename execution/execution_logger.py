from __future__ import annotations

import json
import os
import time
import uuid
from threading import Lock
from typing import Dict, List, Optional

from infrastructure.persistence import ActionRecord, get_persistence

LOG_FILE = "execution_logs.json"
MAX_LOG_SIZE_MB = 10


class ExecutionLogger:
    """
    Persistent execution journal with:
    - JSONL trace log
    - SQLite-backed action history
    - replay helpers
    - stable trace IDs for debugging
    """

    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file
        self._lock = Lock()
        self.persistence = get_persistence()

        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8"):
                pass

    def log(self, decision: Dict, response, latency: float = None) -> str:
        trace_id = self._resolve_trace_id(decision, response)

        try:
            entry = self._build_entry(decision, response, latency, trace_id)

            with self._lock:
                self._rotate_if_needed()
                with open(self.log_file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry) + "\n")

            self._persist_entry(entry)
            return trace_id

        except Exception as exc:
            print("Execution logging failed:", exc)
            return trace_id

    def replay_recent(self, limit: int = 20, status: Optional[str] = None) -> List[Dict]:
        try:
            rows = self.persistence.get_action_history(limit=limit, status=status)
            replay_entries = []
            for row in rows:
                parsed_result = self._safe_loads(row.get("result"))
                parsed_error = self._safe_loads(row.get("error"))
                replay_entries.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "action": row.get("action"),
                        "target": row.get("target"),
                        "status": row.get("status"),
                        "result": parsed_result,
                        "error": parsed_error,
                    }
                )
            return replay_entries
        except Exception:
            return []

    def get_trace(self, trace_id: str) -> List[Dict]:
        if not trace_id or not os.path.exists(self.log_file):
            return []

        matches = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("trace_id") == trace_id:
                        matches.append(data)
        except Exception:
            return []

        return matches

    def _build_entry(self, decision: Dict, response, latency: float, trace_id: str) -> Dict:
        metadata = dict(getattr(response, "metadata", {}) or {})
        metadata.setdefault("trace_id", trace_id)
        if getattr(response, "metadata", None) is not None:
            response.metadata = metadata

        entry = {
            "trace_id": trace_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": decision.get("action"),
            "target": decision.get("target"),
            "parameters": decision.get("parameters"),
            "risk_level": decision.get("risk_level"),
            "requires_confirmation": decision.get("requires_confirmation"),
            "status": decision.get("status"),
            "success": getattr(response, "success", False),
            "error_code": getattr(response, "error_code", None),
            "category": getattr(response, "category", None),
            "spoken_message": getattr(response, "spoken_message", None),
            "technical_message": getattr(response, "technical_message", None),
            "latency_ms": int(latency * 1000) if latency else None,
            "metadata": metadata,
        }
        return entry

    def _persist_entry(self, entry: Dict) -> None:
        status = "success" if entry["success"] else "failed"
        if entry.get("status") == "BLOCKED":
            status = "blocked"

        self.persistence.record_action(
            ActionRecord(
                timestamp=entry["timestamp"],
                action=entry.get("action") or "UNKNOWN",
                target=str(entry.get("target") or ""),
                status=status,
                user="assistant",
                risk_level=int(entry.get("risk_level") or 0),
                confidence=float(entry.get("metadata", {}).get("confidence", 0.0)),
                result=json.dumps(
                    {
                        "spoken_message": entry.get("spoken_message"),
                        "category": entry.get("category"),
                        "metadata": entry.get("metadata"),
                    }
                ),
                error=json.dumps(
                    {
                        "error_code": entry.get("error_code"),
                        "technical_message": entry.get("technical_message"),
                    }
                ) if entry.get("error_code") else None,
            )
        )

        trace_id = entry.get("trace_id")
        if trace_id:
            self.persistence.audit_log(
                event_type="execution_trace",
                event_data={
                    "trace_id": trace_id,
                    "action": entry.get("action"),
                    "success": entry.get("success"),
                    "error_code": entry.get("error_code"),
                },
                user="assistant",
            )

    def _resolve_trace_id(self, decision: Dict, response) -> str:
        metadata = dict(getattr(response, "metadata", {}) or {})
        trace_id = metadata.get("trace_id") or decision.get("trace_id") or str(uuid.uuid4())
        metadata["trace_id"] = trace_id
        if getattr(response, "metadata", None) is not None:
            response.metadata = metadata
        return trace_id

    def _rotate_if_needed(self):
        try:
            if not os.path.exists(self.log_file):
                return

            size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
            if size_mb < MAX_LOG_SIZE_MB:
                return

            rotated = self.log_file.replace(".json", "_old.json")
            if os.path.exists(rotated):
                os.remove(rotated)
            os.rename(self.log_file, rotated)

            with open(self.log_file, "w", encoding="utf-8"):
                pass
        except Exception as exc:
            print("Log rotation failed:", exc)

    def _safe_loads(self, value):
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value
