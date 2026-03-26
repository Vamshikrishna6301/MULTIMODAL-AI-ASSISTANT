import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from execution.accessibility.accessibility_navigator import AccessibilityNavigator


print("\n==============================")
print(" SCREEN DETECTION TEST")
print("==============================\n")

navigator = AccessibilityNavigator()

elements, speech = navigator.read_screen()

print("\n--- SCREEN OUTPUT ---\n")

print(speech)

print("\n--- ELEMENT COUNT ---")

if elements:
    print(f"Detected {len(elements)} UI elements\n")

    for el in elements[:20]:
        print(el.speakable())

else:
    print("No elements detected")