import time
import pyautogui
from core.response_model import UnifiedResponse


class WindowsKeyboardAdapter:
    """
    Production-Level Keyboard Adapter

    Improvements:
    - typing interval control
    - max length safety
    - focus delay
    """

    MAX_TEXT_LENGTH = 500

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02

    def type_text(self, text: str) -> UnifiedResponse:

        if not text:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="No text was provided to type.",
                error_code="NO_TEXT"
            )

        if len(text) > self.MAX_TEXT_LENGTH:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="The text is too long to type safely.",
                error_code="TEXT_TOO_LONG"
            )

        try:
            time.sleep(1)  # allow window focus

            pyautogui.write(text, interval=0)

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message="Text typed successfully."
            )

        except pyautogui.FailSafeException:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Typing stopped due to fail-safe trigger.",
                error_code="FAIL_SAFE_TRIGGERED"
            )

        except Exception as e:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Typing failed.",
                error_code="TYPE_ERROR",
                technical_message=str(e)
            )

    def undo_last_input(self) -> bool:

        try:
            pyautogui.hotkey("ctrl", "z")
            return True

        except Exception:
            return False
