from pynput import keyboard
import time


class KeyboardNavigator:
    """
    Production keyboard navigation controller.

    Handles keyboard navigation similar to screen readers.

    Supported keys:
    TAB           → next item
    SHIFT + TAB   → previous item
    ENTER         → activate
    SPACE         → read current element
    ESC           → cancel

    Designed to cooperate with UIA focus events.
    """

    def __init__(self, navigator, speak):

        self.navigator = navigator
        self.speak = speak

        self.listener = None

        # track modifier state
        self.shift_pressed = False

        # debounce protection
        self.last_action_time = 0
        self.debounce = 0.08

    # -------------------------------------------------

    def _can_trigger(self):

        now = time.time()

        if now - self.last_action_time < self.debounce:
            return False

        self.last_action_time = now
        return True

    # -------------------------------------------------

    def on_press(self, key):

        try:

            if key == keyboard.Key.shift:
                self.shift_pressed = True
                return

            if not self._can_trigger():
                return

            # TAB navigation
            if key == keyboard.Key.tab:

                if self.shift_pressed:
                    text = self.navigator.previous_item()
                else:
                    text = self.navigator.next_item()

                if text:
                    self.speak(text)

            # ENTER activation
            elif key == keyboard.Key.enter:

                text = self.navigator.activate()

                if text:
                    self.speak(text)

            # SPACE read current
            elif key == keyboard.Key.space:

                text = self.navigator.read_current()

                if text:
                    self.speak(text)

            # ESC cancel
            elif key == keyboard.Key.esc:

                self.speak("Cancelled")

        except Exception:
            pass

    # -------------------------------------------------

    def on_release(self, key):

        try:

            if key == keyboard.Key.shift:
                self.shift_pressed = False

        except Exception:
            pass

    # -------------------------------------------------

    def start(self):

        if self.listener:
            return

        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )

        self.listener.daemon = True
        self.listener.start()

    # -------------------------------------------------

    def stop(self):

        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
        except Exception:
            pass