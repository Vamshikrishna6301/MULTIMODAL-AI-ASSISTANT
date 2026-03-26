import sys
import os

# Add project root so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from execution.accessibility.accessibility_navigator import AccessibilityNavigator


print("\n==============================")
print(" TREE NAVIGATION TEST")
print("==============================\n")

nav = AccessibilityNavigator()

print("Scanning screen...\n")

nav.refresh_elements()

print("Total elements detected:", len(nav.state.elements))
print()

print("Testing NEXT navigation:\n")

for i in range(10):

    text = nav.next_item()

    print(text)

input("\nPress ENTER to exit...")