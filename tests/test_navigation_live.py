import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from execution.accessibility.accessibility_navigator import AccessibilityNavigator

navigator = AccessibilityNavigator()

print("\nAccessibility Navigation Test\n")

while True:

    cmd = input(
        "\nCommands:\n"
        "r = read screen\n"
        "n = next item\n"
        "b = next button\n"
        "i = next input\n"
        "l = next link\n"
        "a = activate\n"
        "q = quit\n\n> "
    )

    if cmd == "r":
        _, speech = navigator.read_screen()
        print("\n", speech)

    elif cmd == "n":
        print(navigator.next_item())

    elif cmd == "b":
        print(navigator.next_button())

    elif cmd == "i":
        print(navigator.next_input())

    elif cmd == "l":
        print(navigator.next_link())

    elif cmd == "a":
        print(navigator.activate())

    elif cmd == "q":
        break