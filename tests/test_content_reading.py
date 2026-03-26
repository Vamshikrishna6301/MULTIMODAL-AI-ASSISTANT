import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
from execution.accessibility.accessibility_navigator import AccessibilityNavigator

navigator = AccessibilityNavigator()

print("\nReading page content...\n")

result = navigator.read_content()

print(result)