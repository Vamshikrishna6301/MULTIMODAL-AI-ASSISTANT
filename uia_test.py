from pywinauto import Desktop
from pywinauto import Application
import time

print("Switch to Notepad in 3 seconds...")
time.sleep(3)

try:
    desktop = Desktop(backend="uia")
    window = desktop.window(active_only=True)
    window.set_focus()
except Exception as e:
    print("Failed to get active window:", e)
    exit()

print("Active Window Title:", window.window_text())
print("\nListing children...\n")


def traverse(element, depth=0, max_depth=4):
    if depth > max_depth:
        return

    try:
        children = element.children()
    except Exception:
        return

    for child in children:
        try:
            name = child.window_text()
            control_type = child.element_info.control_type

            if name:
                print("  " * depth + f"[{control_type}] {name}")

            traverse(child, depth + 1)

        except Exception:
            continue


traverse(window)