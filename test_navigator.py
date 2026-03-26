from execution.accessibility.accessibility_navigator import AccessibilityNavigator


def run_test():

    print("\n==============================")
    print(" ACCESSIBILITY NAVIGATOR TEST ")
    print("==============================\n")

    navigator = AccessibilityNavigator(None, None)

    # ---------------------------------
    # READ SCREEN
    # ---------------------------------

    print("\n--- READ SCREEN ---\n")

    elements, speech = navigator.read_screen()

    print(speech)

    # ---------------------------------
    # BASIC NAVIGATION TEST
    # ---------------------------------

    print("\n--- NAVIGATION TEST ---\n")

    for i in range(5):
        print("NEXT:", navigator.next_item())

    print("\n--- PREVIOUS ITEM ---\n")

    print("PREVIOUS:", navigator.previous_item())

    # ---------------------------------
    # SEMANTIC NAVIGATION
    # ---------------------------------

    print("\n--- NEXT BUTTON ---\n")

    print("BUTTON:", navigator.next_button())

    print("\n--- NEXT INPUT ---\n")

    print("INPUT:", navigator.next_input())

    # ---------------------------------
    # CURRENT ELEMENT
    # ---------------------------------

    print("\n--- CURRENT ELEMENT ---\n")

    print("CURRENT:", navigator.read_current())

    print("\n==============================")
    print(" TEST COMPLETE (SAFE MODE)")
    print("==============================\n")


if __name__ == "__main__":
    run_test()