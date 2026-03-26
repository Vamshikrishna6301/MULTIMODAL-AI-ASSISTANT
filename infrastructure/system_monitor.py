"""
PRODUCTION HEALTH MONITORING
System health checks, metrics collection, and performance monitoring
"""

import os
import threading
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - dependency may be absent
    psutil = None

from config_production import MONITORING_CONFIG
from infrastructure.logger import get_logger


class _FallbackMemory:
    def __init__(self, total: int, available: int):
        self.total = total
        self.available = available
        self.used = max(0, total - available)
        self.percent = (self.used / total * 100) if total else 0.0


def _virtual_memory():
    if psutil:
        return psutil.virtual_memory()
    if hasattr(os, "sysconf"):
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        avail_pages = os.sysconf("SC_AVPHYS_PAGES")
        return _FallbackMemory(
            total=int(page_size * phys_pages),
            available=int(page_size * avail_pages),
        )
    return _FallbackMemory(total=0, available=0)


@dataclass
class HealthStatus:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    gpu_memory_mb: Optional[float]
    gpu_utilization: Optional[float]
    active_threads: int
    status: str


class SystemHealthMonitor:
    def __init__(self):
        self.logger = get_logger("health")
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_status: Optional[HealthStatus] = None
        self.metrics_history: list = []
        self.max_history = 1000

        self.cpu_warning_threshold = 80
        self.cpu_critical_threshold = 95
        self.memory_warning_threshold = 90
        self.memory_critical_threshold = 97

    def start(self):
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HealthMonitor"
        )
        self.monitor_thread.start()
        self.logger.debug("Health monitoring started")

    def stop(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.debug("Health monitoring stopped")

    def _monitor_loop(self):
        while self.monitoring:
            try:
                self.last_status = self._get_status()
                self._check_thresholds(self.last_status)
                self.metrics_history.append(self.last_status)

                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)

                time.sleep(MONITORING_CONFIG["metrics_update_interval"])

            except Exception as e:
                self.logger.error("Monitoring error", exception=e)

    def _get_status(self) -> HealthStatus:
        cpu_percent = psutil.cpu_percent(interval=0.1) if psutil else 0.0
        memory = _virtual_memory()

        gpu_memory_mb = None
        gpu_utilization = None

        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory_mb = torch.cuda.memory_allocated() / 1024 / 1024
        except Exception:
            pass

        status = self._determine_status(cpu_percent, memory.percent)

        return HealthStatus(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_mb=memory.used / 1024 / 1024,
            gpu_memory_mb=gpu_memory_mb,
            gpu_utilization=gpu_utilization,
            active_threads=threading.active_count(),
            status=status
        )

    def _determine_status(self, cpu: float, memory: float) -> str:
        if cpu > self.cpu_critical_threshold or memory > self.memory_critical_threshold:
            return "critical"
        elif cpu > self.cpu_warning_threshold or memory > self.memory_warning_threshold:
            return "warning"
        return "healthy"

    def _check_thresholds(self, status: HealthStatus):

        if not hasattr(self, "_last_logged_status"):
            self._last_logged_status = None

        # Only log if status changed
        if status.status == self._last_logged_status:
            return

        self._last_logged_status = status.status

        if status.status == "critical":
            self.logger.warning(
                "CRITICAL resource usage",
                cpu=status.cpu_percent,
                memory=status.memory_percent
            )
        elif status.status == "warning":
            self.logger.warning(
                "WARNING resource usage",
                cpu=status.cpu_percent,
                memory=status.memory_percent
            )
    def get_status(self) -> Optional[HealthStatus]:
        return self.last_status

    def get_metrics(self) -> Dict[str, Any]:
        if not self.last_status:
            return {}

        s = self.last_status
        return {
            "timestamp": s.timestamp.isoformat(),
            "cpu_percent": s.cpu_percent,
            "memory_percent": s.memory_percent,
            "memory_mb": s.memory_mb,
            "gpu_memory_mb": s.gpu_memory_mb,
            "active_threads": s.active_threads,
            "status": s.status,
        }


class PerformanceTracker:
    def __init__(self):
        self.logger = get_logger("performance")
        self.timings: Dict[str, list] = {}

    def record_timing(self, component: str, duration_ms: float):
        if component not in self.timings:
            self.timings[component] = []

        self.timings[component].append(duration_ms)

        if len(self.timings[component]) > 1000:
            self.timings[component] = self.timings[component][-500:]

    def get_stats(self, component: str) -> Dict[str, float]:
        if component not in self.timings or not self.timings[component]:
            return {}

        timings = self.timings[component]
        return {
            "count": len(timings),
            "avg_ms": sum(timings) / len(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
        }

    def log_stats(self):
        for component in self.timings:
            stats = self.get_stats(component)
            if stats:
                self.logger.info("performance_metrics", component=component, **stats)


class ResourceCleaner:
    def __init__(self):
        self.logger = get_logger("cleanup")

    def cleanup_torch_cache(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                self.logger.debug("PyTorch cache cleaned")
        except Exception as e:
            self.logger.debug("PyTorch cleanup skipped", exception=e)

    def optimize_memory(self):
        import gc
        gc.collect()
        self.logger.debug("Memory optimization triggered")

    def cleanup_all(self):
        self.cleanup_torch_cache()
        self.optimize_memory()


_health_monitor: Optional[SystemHealthMonitor] = None
_performance_tracker: Optional[PerformanceTracker] = None
_resource_cleaner: Optional[ResourceCleaner] = None


def get_health_monitor() -> SystemHealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor()
    return _health_monitor


def get_performance_tracker() -> PerformanceTracker:
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker


def get_resource_cleaner() -> ResourceCleaner:
    global _resource_cleaner
    if _resource_cleaner is None:
        _resource_cleaner = ResourceCleaner()
    return _resource_cleaner
