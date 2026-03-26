import win32gui
from pywinauto import Application

# get the handle of the currently focused window
hwnd = win32gui.GetForegroundWindow()

# connect pywinauto to that window
app = Application(backend="uia").connect(handle=hwnd)

window = app.window(handle=hwnd)

print("Active Window:", window.window_text())

elements = window.descendants()

print("\nFirst 20 UI elements:\n")

for el in elements[:20]:
    try:
        name = el.window_text()
        role = el.friendly_class_name()

        if name:
            print(role, ":", name)
    except:
        pass