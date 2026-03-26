import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
from execution.accessibility.focus_event_monitor import FocusEventMonitor

print("\n==============================")
print(" NVDA FOCUS MONITOR TEST")
print("==============================\n")

print("Instructions:")
print("1. Open Chrome / VS Code / Notepad")
print("2. Press TAB repeatedly")
print("3. Observe spoken elements\n")

monitor = FocusEventMonitor()

monitor.start()

print("Focus monitor running. Press CTRL+C to stop.\n")

try:
    while True:
        pass
except KeyboardInterrupt:
    monitor.stop()
    print("\nTest stopped.")