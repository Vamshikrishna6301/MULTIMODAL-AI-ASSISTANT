from __future__ import annotations

import time
from typing import Dict, Optional

from core.response_model import UnifiedResponse
from infrastructure.cache import get_cache
from infrastructure.system_monitor import get_performance_tracker


class PerformanceOptimizationLayer:
    """
    Adaptive short-lived response caching and timing for hot execution paths.
    """

    CACHEABLE_ACTIONS = {
        "READ_SCREEN": 1.0,
        "VISION": 1.0,
        "GET_TIME": 0.5,
        "PLUGIN": 1.5,
    }

    def __init__(self):
        self.cache = get_cache()
        self.performance_tracker = get_performance_tracker()

    def build_cache_key(self, decision: Dict) -> Optional[str]:
        action = decision.get("action")
        if action not in self.CACHEABLE_ACTIONS:
            return None

        payload = {
            "action": action,
            "target": str(decision.get("target")),
            "parameters": str(decision.get("parameters", {})),
        }
        return f"response:{payload}"

    def get_cached_response(self, decision: Dict) -> Optional[UnifiedResponse]:
        key = self.build_cache_key(decision)
        if not key:
            return None
        return self.cache.get(key)

    def store_response(self, decision: Dict, response: UnifiedResponse):
        if not response.success:
            return
        key = self.build_cache_key(decision)
        if not key:
            return
        ttl = self.CACHEABLE_ACTIONS.get(decision.get("action"), 0)
        if ttl > 0:
            self.cache.set(key, response, ttl_seconds=max(0.1, ttl))

    def record_timing(self, component: str, start_time: float):
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.performance_tracker.record_timing(component, duration_ms)
        return duration_ms
