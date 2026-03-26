import win32gui


def is_browser():

    try:

        window = win32gui.GetForegroundWindow()

        title = win32gui.GetWindowText(window)

        return "chrome" in title.lower()

    except Exception:
        return False