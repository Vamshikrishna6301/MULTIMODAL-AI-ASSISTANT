"""
Production-Grade Health Monitoring & Metrics
Real-time system health checks and performance metrics
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum
import os
import shutil
import time

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - dependency may be absent in production
    psutil = None
from infrastructure.logger import get_logger

logger = get_logger(__name__)


class _FallbackMemory:
    def __init__(self, total: int, available: int):
        self.total = total
        self.available = available
        used = max(0, total - available)
        self.used = used
        self.percent = (used / total * 100) if total else 0.0


class _FallbackDisk:
    def __init__(self, total: int, free: int):
        self.total = total
        self.free = free
        used = max(0, total - free)
        self.used = used
        self.percent = (used / total * 100) if total else 0.0


def _virtual_memory():
    if psutil:
        return psutil.virtual_memory()
    total = 0
    available = 0
    if hasattr(os, "sysconf"):
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        avail_pages = os.sysconf("SC_AVPHYS_PAGES")
        total = int(page_size * phys_pages)
        available = int(page_size * avail_pages)
    return _FallbackMemory(total=total, available=available)


def _disk_usage(path: str):
    if psutil:
        return psutil.disk_usage(path)
    usage = shutil.disk_usage(path)
    return _FallbackDisk(total=usage.total, free=usage.free)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Dict = field(default_factory=dict)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: str
    value: float
    unit: str


@dataclass
class HealthReport:
    """Complete health report"""
    timestamp: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    metrics: Dict[str, float]
    uptime_seconds: float


class MetricsCollector:
    """Collect and track system metrics"""

    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.start_time = time.time()
        self.max_history_points = 1000

    def record_metric(self, name: str, value: float, unit: str = ""):
        """Record a metric value"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        point = MetricPoint(
            timestamp=datetime.utcnow().isoformat(),
            value=value,
            unit=unit
        )
        
        self.metrics[name].append(point)
        
        # Keep only recent history
        if len(self.metrics[name]) > self.max_history_points:
            self.metrics[name] = self.metrics[name][-self.max_history_points:]

    def get_metric(self, name: str) -> Optional[MetricPoint]:
        """Get latest metric value"""
        if name in self.metrics and self.metrics[name]:
            return self.metrics[name][-1]
        return None

    def get_metric_average(self, name: str, window_seconds: int = 300) -> Optional[float]:
        """Get average metric value over time window"""
        if name not in self.metrics:
            return None
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        values = [
            point.value for point in self.metrics[name]
            if datetime.fromisoformat(point.timestamp) > cutoff_time
        ]
        
        if values:
            return sum(values) / len(values)
        return None

    def get_all_metrics(self) -> Dict[str, float]:
        """Get latest values for all metrics"""
        return {
            name: points[-1].value
            for name, points in self.metrics.items()
            if points
        }


class HealthMonitor:
    """
    System health monitoring
    - Performs regular health checks
    - Tracks metrics
    - Generates health reports
    """

    def __init__(self):
        self.metrics = MetricsCollector()
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, HealthCheckResult] = {}

    def register_health_check(self, name: str, check_func: Callable[[], bool]):
        """Register a custom health check"""
        self.health_checks[name] = check_func

    def add_system_checks(self):
        """Add default system health checks"""
        self.register_health_check("cpu", self._check_cpu)
        self.register_health_check("memory", self._check_memory)
        self.register_health_check("disk", self._check_disk)
        self.register_health_check("process", self._check_process)

    def _check_cpu(self) -> HealthCheckResult:
        """Check CPU usage"""
        start = time.time()
        try:
            cpu_percent = psutil.cpu_percent(interval=1) if psutil else 0.0
            response_time = (time.time() - start) * 1000
            
            self.metrics.record_metric("cpu_usage", cpu_percent, "%")
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage: {cpu_percent}%"
            elif cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical CPU usage: {cpu_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage normal: {cpu_percent}%"
            
            return HealthCheckResult(
                name="cpu",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={"cpu_percent": cpu_percent}
            )
        except Exception as e:
            logger.error("CPU check failed", exception=str(e))
            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"CPU check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    def _check_memory(self) -> HealthCheckResult:
        """Check memory usage"""
        start = time.time()
        try:
            memory = _virtual_memory()
            response_time = (time.time() - start) * 1000
            
            self.metrics.record_metric("memory_usage", memory.percent, "%")
            
            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent}%"
            elif memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent}%"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "memory_percent": memory.percent,
                    "available_mb": memory.available / (1024 * 1024)
                }
            )
        except Exception as e:
            logger.error("Memory check failed", exception=str(e))
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    def _check_disk(self) -> HealthCheckResult:
        """Check disk usage"""
        start = time.time()
        try:
            disk = _disk_usage(os.path.abspath(os.sep))
            response_time = (time.time() - start) * 1000
            
            self.metrics.record_metric("disk_usage", disk.percent, "%")
            
            if disk.percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {disk.percent}%"
            elif disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {disk.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {disk.percent}%"
            
            return HealthCheckResult(
                name="disk",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "disk_percent": disk.percent,
                    "free_gb": disk.free / (1024 * 1024 * 1024)
                }
            )
        except Exception as e:
            logger.error("Disk check failed", exception=str(e))
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    def _check_process(self) -> HealthCheckResult:
        """Check process health"""
        start = time.time()
        try:
            response_time = (time.time() - start) * 1000
            if psutil:
                process = psutil.Process()
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                rss_bytes = memory_info.rss
            else:
                cpu_percent = 0.0
                rss_bytes = 0
            
            self.metrics.record_metric("process_cpu", cpu_percent, "%")
            self.metrics.record_metric("process_memory_mb", rss_bytes / (1024 * 1024), "MB")
            
            return HealthCheckResult(
                name="process",
                status=HealthStatus.HEALTHY,
                message="Process running normally",
                response_time_ms=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_mb": rss_bytes / (1024 * 1024),
                    "num_threads": process.num_threads()
                }
            )
        except Exception as e:
            logger.error("Process check failed", exception=str(e))
            return HealthCheckResult(
                name="process",
                status=HealthStatus.UNKNOWN,
                message=f"Process check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    def run_checks(self) -> HealthReport:
        """Run all health checks"""
        logger.info("Running health checks")
        
        results = []
        
        # Run default checks
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results.append(result)
                self.last_check_results[check_name] = result
            except Exception as e:
                logger.error(f"Health check failed", check=check_name, exception=str(e))
                result = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed: {str(e)}",
                    response_time_ms=0
                )
                results.append(result)

        # Determine overall status
        statuses = [r.status for r in results]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        uptime = time.time() - self.metrics.start_time

        report = HealthReport(
            timestamp=datetime.utcnow().isoformat(),
            overall_status=overall_status,
            checks=results,
            metrics=self.metrics.get_all_metrics(),
            uptime_seconds=uptime
        )

        logger.info(
            "Health check completed",
            overall_status=overall_status.value,
            uptime_seconds=uptime
        )

        return report

    def get_health_json(self) -> Dict:
        """Get health report as JSON"""
        report = self.run_checks()
        return {
            "timestamp": report.timestamp,
            "status": report.overall_status.value,
            "uptime_seconds": report.uptime_seconds,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for check in report.checks
            ],
            "metrics": report.metrics
        }


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def init_health_monitor() -> HealthMonitor:
    """Initialize global health monitor"""
    global _health_monitor
    _health_monitor = HealthMonitor()
    _health_monitor.add_system_checks()
    return _health_monitor


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
        _health_monitor.add_system_checks()
    return _health_monitor
