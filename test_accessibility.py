import win32gui
from pywinauto import Application
from execution.accessibility.safe_ui_scan import safe_scan

# get the handle of the currently focused window
hwnd = win32gui.GetForegroundWindow()

# connect pywinauto to that window
app = Application(backend="uia").connect(handle=hwnd)

window = app.window(handle=hwnd)

print("Active Window:", window.window_text())

print("\nFirst 20 UI elements:\n")
for role, name in safe_scan(window)[:20]:
    if name:
        print(role, ":", name)
