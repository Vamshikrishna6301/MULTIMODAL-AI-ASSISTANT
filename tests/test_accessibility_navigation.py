import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from execution.accessibility.accessibility_navigator import AccessibilityNavigator
from execution.uia_service.uia_client import UIAClient
from execution.vision.vision_executor import VisionExecutor


def main():

    uia_client = UIAClient()
    vision_executor = VisionExecutor()

    navigator = AccessibilityNavigator(uia_client, vision_executor)

    print("\n--- TEST 1 : READ SCREEN ---")
    elements, speech = navigator.read_screen()
    print(speech)

    print("\n--- TEST 2 : NEXT ITEM ---")
    print(navigator.next_item())

    print("\n--- TEST 3 : PREVIOUS ITEM ---")
    print(navigator.previous_item())

    print("\n--- TEST 4 : NEXT BUTTON ---")
    print(navigator.next_button())

    print("\n--- TEST 5 : NEXT INPUT ---")
    print(navigator.next_input())

    print("\n--- TEST 6 : NEXT LINK ---")
    print(navigator.next_link())

    print("\n--- TEST 7 : NEXT CHAT ---")
    print(navigator.next_chat())

    print("\n--- TEST 8 : NEXT MESSAGE ---")
    print(navigator.next_message())

    print("\n--- TEST 9 : FOCUS INPUT ---")
    print(navigator.focus_input())

    print("\n--- TEST 10 : ACTIVATE ITEM ---")
    print(navigator.activate())

    print("\n--- TEST 11 : READ CURRENT ---")
    print(navigator.read_current())

    print("\n--- TEST 12 : READ CONVERSATION ---")
    print(navigator.read_conversation())


if __name__ == "__main__":
    main()