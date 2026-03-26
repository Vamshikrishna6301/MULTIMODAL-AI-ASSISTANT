import subprocess
from core.response_model import UnifiedResponse


class WindowsSystemAdapter:
    """
    Windows System Control Adapter
    Handles:
    - Close application
    - Shutdown
    - Restart
    """

    # =====================================================
    # CLOSE APPLICATION
    # =====================================================

    def close_application(self, target: str) -> UnifiedResponse:

        if not target:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="No application specified to close.",
                error_code="NO_TARGET"
            )

        target = target.lower().strip()

        try:

            result = subprocess.call(
                ["taskkill", "/IM", f"{target}.exe", "/F"]
            )

            if result == 0:
                return UnifiedResponse.success_response(
                    category="execution",
                    spoken_message=f"{target} closed."
                )

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message=f"Could not close {target}. It may not be running.",
                error_code="PROCESS_NOT_FOUND"
            )

        except Exception as e:

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message=f"Failed to close {target}.",
                error_code="CLOSE_FAILED",
                technical_message=str(e)
            )

    # =====================================================
    # MAIN HANDLER
    # =====================================================

    def handle(self, decision: dict) -> UnifiedResponse:

        action = decision.get("action")
        target = decision.get("target", "")
        text = decision.get("text", "").lower()

        if action == "SYSTEM_CONTROL" and target:
            return self.close_application(target)

        if "shutdown" in text:

            subprocess.call(["shutdown", "/s", "/t", "5"])

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message="System shutting down."
            )

        if "restart" in text:

            subprocess.call(["shutdown", "/r", "/t", "5"])

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message="System restarting."
            )

        return UnifiedResponse.error_response(
            category="execution",
            spoken_message="Unsupported system control command.",
            error_code="SYSTEM_UNSUPPORTED"
        )