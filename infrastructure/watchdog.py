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
        self._consecutive_failures: Dict[str, int] = {}

    def register(self, component: str, timeout_seconds: float = 10.0):
        with self._lock:
            self._timeouts[component] = timeout_seconds
            self._heartbeats[component] = time.monotonic()
            self._consecutive_failures[component] = 0

    def heartbeat(self, component: str):
        with self._lock:
            if component not in self._timeouts:
                self._timeouts[component] = 10.0
            if component not in self._consecutive_failures:
                self._consecutive_failures[component] = 0
            self._heartbeats[component] = time.monotonic()
            self._consecutive_failures[component] = 0

    def recover_timeout(
        self,
        component: str,
        *,
        cancel_navigation_worker=None,
        clear_command_queue=None,
    ) -> bool:
        with self._lock:
            failures = self._consecutive_failures.get(component, 0) + 1
            self._consecutive_failures[component] = failures

        if callable(cancel_navigation_worker):
            try:
                cancel_navigation_worker()
            except Exception:
                pass

        if callable(clear_command_queue):
            try:
                clear_command_queue()
            except Exception:
                pass

        return failures >= 3

    def consecutive_failures(self, component: str) -> int:
        with self._lock:
            return self._consecutive_failures.get(component, 0)

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
