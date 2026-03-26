import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)
import keyboard
from execution.accessibility.accessibility_navigator import AccessibilityNavigator

navigator = AccessibilityNavigator()

print("\nAccessibility Navigation Hotkey Test\n")

print("F1  = read screen")
print("F2  = next item")
print("F6  = next button")
print("F7  = next input")
print("F8  = next link")
print("F9 = activate")


def read_screen():
    _, speech = navigator.read_screen()
    print("\n", speech)


def next_item():
    print(navigator.next_item())


def next_button():
    print(navigator.next_button())


def next_input():
    print(navigator.next_input())


def next_link():
    print(navigator.next_link())


def activate():
    print(navigator.activate())


keyboard.add_hotkey("F1", read_screen)
keyboard.add_hotkey("F2", next_item)
keyboard.add_hotkey("F6", next_button)
keyboard.add_hotkey("F7", next_input)
keyboard.add_hotkey("F8", next_link)
keyboard.add_hotkey("F9", activate)

keyboard.wait("esc")