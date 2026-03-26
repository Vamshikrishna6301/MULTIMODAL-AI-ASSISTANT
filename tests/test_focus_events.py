import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from execution.accessibility.navigation_state import NavigationState
from execution.accessibility.uia_focus_event_listener import UIFocusEventListener

def speak(msg):
    print(msg)

state = NavigationState()

listener = UIFocusEventListener(speak, state)
listener.start()

print("Focus listener started.")
print("Click around different UI elements.")

input("Press ENTER to exit")