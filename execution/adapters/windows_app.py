import subprocess
import shutil
import os

from core.response_model import UnifiedResponse


class WindowsAppAdapter:
    """
    Production-Level Windows App Launcher

    Improvements:
    - System32 fallback resolution
    - Safe executable normalization
    - Detached process launch
    - Prevent arbitrary path execution
    """

    COMMON_APPS = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "explorer": "explorer.exe"
    }

    SYSTEM32 = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32")

    # =====================================================

    def open_app(self, app_name: str) -> UnifiedResponse:

        if not app_name:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="No application name was provided.",
                error_code="NO_APP_NAME"
            )

        app_name = app_name.lower().strip()

        # Prevent path injection
        if "\\" in app_name or "/" in app_name:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Opening arbitrary paths is not allowed.",
                error_code="INVALID_APP_PATH"
            )

        # Remove .exe if user spoke it
        if app_name.endswith(".exe"):
            app_name = app_name[:-4]

        if app_name == "camera":
            try:
                subprocess.Popen("start microsoft.windows.camera:", shell=True)
                return UnifiedResponse.success_response(
                    category="execution",
                    spoken_message="Opening camera."
                )
            except Exception as e:
                return UnifiedResponse.error_response(
                    category="execution",
                    spoken_message="Failed to open the application.",
                    error_code="APP_OPEN_FAILED",
                    technical_message=str(e)
                )

        # Resolve alias
        resolved = self.COMMON_APPS.get(app_name, app_name)

        if not resolved.endswith(".exe"):
            resolved += ".exe"

        # --------------------------------------------------
        # Try resolving in PATH
        # --------------------------------------------------

        executable = shutil.which(resolved)

        # --------------------------------------------------
        # Fallback: System32
        # --------------------------------------------------

        if not executable:

            system_path = os.path.join(self.SYSTEM32, resolved)

            if os.path.exists(system_path):
                executable = system_path

        # --------------------------------------------------
        # Not found
        # --------------------------------------------------

        if not executable:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message=f"I could not find an application named {app_name}.",
                error_code="APP_NOT_FOUND"
            )

        # --------------------------------------------------
        # Launch application
        # --------------------------------------------------

        try:

            subprocess.Popen(
                executable,
                creationflags=subprocess.DETACHED_PROCESS
            )

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message=f"Opening {app_name}."
            )

        except Exception as e:

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Failed to open the application.",
                error_code="APP_OPEN_FAILED",
                technical_message=str(e)
            )
