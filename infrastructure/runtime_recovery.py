from __future__ import annotations

from datetime import datetime
from typing import Dict

from infrastructure.persistence import get_persistence


class RuntimeRecoveryManager:
    def __init__(self):
        self.persistence = get_persistence()

    def mark_startup(self):
        self.persistence.set_state(
            "runtime_state",
            {
                "status": "starting",
                "timestamp": datetime.utcnow().isoformat(),
                "clean_shutdown": False,
            },
        )

    def mark_ready(self):
        self.persistence.set_state(
            "runtime_state",
            {
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "clean_shutdown": False,
            },
        )

    def mark_shutdown(self):
        self.persistence.set_state(
            "runtime_state",
            {
                "status": "stopped",
                "timestamp": datetime.utcnow().isoformat(),
                "clean_shutdown": True,
            },
        )

    def get_last_runtime_state(self) -> Dict:
        state = self.persistence.get_state("runtime_state")
        return state or {}

    def needs_recovery(self) -> bool:
        state = self.get_last_runtime_state()
        if not state:
            return False
        return not bool(state.get("clean_shutdown", False))
