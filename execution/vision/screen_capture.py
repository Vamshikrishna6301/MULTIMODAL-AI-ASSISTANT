import mss
import numpy as np
import cv2
import win32gui


class ScreenCapture:
    """
    Thread-safe Screen Capture
    Captures active foreground window
    """

    def capture(self):

        # Create mss instance inside method (thread-safe)
        with mss.mss() as sct:

            hwnd = win32gui.GetForegroundWindow()

            if not hwnd:
                raise RuntimeError("No active window found.")

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)

            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                raise RuntimeError("Invalid active window dimensions.")

            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }

            screenshot = sct.grab(monitor)

            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            return frame