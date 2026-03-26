from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WatchdogStatus:
    component: str
    last_heartbeat: float
    timeout_seconds: float
    healthy: bool


class WatchdogManager:
    """
    Lightweight heartbeat watchdog for critical assistant components.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._heartbeats: Dict[str, float] = {}
        self._timeouts: Dict[str, float] = {}

    def register(self, component: str, timeout_seconds: float = 10.0):
        with self._lock:
            self._timeouts[component] = timeout_seconds
            self._heartbeats[component] = time.monotonic()

    def heartbeat(self, component: str):
        with self._lock:
            if component not in self._timeouts:
                self._timeouts[component] = 10.0
            self._heartbeats[component] = time.monotonic()

    def get_status(self, component: str) -> Optional[WatchdogStatus]:
        with self._lock:
            if component not in self._heartbeats:
                return None
            last = self._heartbeats[component]
            timeout = self._timeouts[component]
            age = time.monotonic() - last
            return WatchdogStatus(
                component=component,
                last_heartbeat=last,
                timeout_seconds=timeout,
                healthy=age <= timeout,
            )

    def get_all_statuses(self):
        with self._lock:
            return [
                self.get_status(component)
                for component in list(self._heartbeats.keys())
            ]


_watchdog: Optional[WatchdogManager] = None


def get_watchdog() -> WatchdogManager:
    global _watchdog
    if _watchdog is None:
        _watchdog = WatchdogManager()
    return _watchdog
