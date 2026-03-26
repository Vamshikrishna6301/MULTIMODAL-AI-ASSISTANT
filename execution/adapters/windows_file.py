import os
from pathlib import Path
from core.response_model import UnifiedResponse


class WindowsFileAdapter:
    """
    Production-Level File Adapter

    Improvements:
    - case-insensitive search
    - path normalization
    - directory traversal protection
    """

    SAFE_DIRECTORIES = [
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads"
    ]

    def handle(self, decision: dict) -> UnifiedResponse:

        target = decision.get("target")

        if not target:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="No file name was provided.",
                error_code="NO_FILE_NAME"
            )

        try:

            file_path = self._find_file_in_safe_dirs(target)

            if not file_path:
                return UnifiedResponse.error_response(
                    category="execution",
                    spoken_message=f"I could not find a file named {target} in safe folders.",
                    error_code="FILE_NOT_FOUND"
                )

            os.remove(file_path)

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message=f"The file {file_path.name} has been deleted."
            )

        except PermissionError:

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Permission denied while trying to delete the file.",
                error_code="PERMISSION_DENIED"
            )

        except Exception as e:

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="File operation failed.",
                error_code="FILE_OPERATION_FAILED",
                technical_message=str(e)
            )

    # -----------------------------------------------------

    def _find_file_in_safe_dirs(self, filename: str):

        filename = filename.lower()

        for directory in self.SAFE_DIRECTORIES:

            try:
                for file in directory.iterdir():

                    if file.is_file() and file.name.lower() == filename:
                        return file

            except Exception:
                continue

        return None