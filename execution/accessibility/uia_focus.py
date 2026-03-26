from pywinauto import Desktop
import win32gui


def get_focused_window():

    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return None

        window = Desktop(backend="uia").window(handle=hwnd)

        return window

    except Exception:
        return None
