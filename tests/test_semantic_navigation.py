import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
from execution.accessibility.accessibility_navigator import AccessibilityNavigator
import time

navigator = AccessibilityNavigator()

print("\n==============================")
print(" SEMANTIC NAVIGATION TEST")
print("==============================\n")

print("Scanning screen...\n")

elements, speech = navigator.read_screen()

print(speech)
print("\nTotal elements detected:", len(elements))
print("\n")

time.sleep(2)

print("Testing NEXT BUTTON navigation:\n")

for _ in range(5):
    result = navigator.next_button()
    print(result)
    time.sleep(1)

print("\nTesting NEXT INPUT navigation:\n")

for _ in range(5):
    result = navigator.next_input()
    print(result)
    time.sleep(1)

print("\nTesting NEXT LINK navigation:\n")

for _ in range(5):
    result = navigator.next_link()
    print(result)
    time.sleep(1)

input("\nPress ENTER to exit...")