import time

from core.response_model import UnifiedResponse
from execution.performance_layer import PerformanceOptimizationLayer
from infrastructure.runtime_recovery import RuntimeRecoveryManager
from infrastructure.watchdog import WatchdogManager


def test_performance_layer_caches_cacheable_response():
    layer = PerformanceOptimizationLayer()
    decision = {"action": "GET_TIME", "target": "", "parameters": {}}
    response = UnifiedResponse.success_response(category="utility", spoken_message="The current time is 01:00 PM.")

    layer.store_response(decision, response)
    cached = layer.get_cached_response(decision)

    assert cached is not None
    assert cached.spoken_message == response.spoken_message


def test_watchdog_marks_stale_component_unhealthy():
    watchdog = WatchdogManager()
    watchdog.register("voice_loop", timeout_seconds=0.05)
    time.sleep(0.07)

    status = watchdog.get_status("voice_loop")

    assert status is not None
    assert status.healthy is False


def test_watchdog_heartbeat_recovers_component_health():
    watchdog = WatchdogManager()
    watchdog.register("execution_engine", timeout_seconds=0.1)
    time.sleep(0.05)
    watchdog.heartbeat("execution_engine")

    status = watchdog.get_status("execution_engine")

    assert status is not None
    assert status.healthy is True


def test_runtime_recovery_detects_unclean_shutdown():
    recovery = RuntimeRecoveryManager()
    recovery.mark_startup()

    assert recovery.needs_recovery() is True

    recovery.mark_shutdown()

    assert recovery.needs_recovery() is False
