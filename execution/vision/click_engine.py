# vision/click_engine.py

import pyautogui


class ClickEngine:
    """
    Robust click executor with multiple fallback strategies.
    """

    def __init__(self, uia_client=None):
        self.uia_client = uia_client

    # =====================================================
    # MAIN CLICK FUNCTION
    # =====================================================

    def click(self, element):

        if element.source == "UIA":
            return self._click_uia(element)

        if element.source in {"OCR", "VISION"}:
            return self._click_bbox(element)

        return False

    # =====================================================
    # UI AUTOMATION CLICK
    # =====================================================

    def _click_uia(self, element):

        try:
            if not self.uia_client:
                return False

            name = element.name

            result = self.uia_client.click_by_name(name)

            if result.get("status") == "success":
                return True

        except Exception:
            pass

        return False

    # =====================================================
    # BBOX CLICK
    # =====================================================

    def _click_bbox(self, element):

        try:

            x, y = element.center()

            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.click()

            return True

        except Exception:
            return False
