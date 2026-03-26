from __future__ import annotations

from core.response_model import UnifiedResponse
from execution.plugin_system import AssistantPlugin
from infrastructure.system_monitor import get_health_monitor


class SystemStatusPlugin(AssistantPlugin):
    plugin_id = "system_status"
    name = "System Status"
    version = "1.0"
    command_patterns = [
        r"\b(system status|system health|health status)\b",
        r"\bhow is the system doing\b",
    ]

    def handle(self, decision):
        monitor = get_health_monitor()
        status = monitor.get_metrics() or {"status": "unknown"}
        spoken = (
            f"System status is {status.get('status', 'unknown')}. "
            f"CPU {round(status.get('cpu_percent', 0), 1)} percent, "
            f"memory {round(status.get('memory_percent', 0), 1)} percent."
        )
        return UnifiedResponse.success_response(
            category="plugin",
            spoken_message=spoken,
            metadata={"plugin_id": self.plugin_id, "metrics": status},
        )
