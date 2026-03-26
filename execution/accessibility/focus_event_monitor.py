import threading
import time

from execution.accessibility.uia_client import uia_client


class FocusEventMonitor:
    """
    NVDA-style focus tracking.

    Continuously monitors UIA focus changes and announces them.
    """

    def __init__(self, tts_engine=None):

        self.running = False
        self.last_element = None
        self.last_spoken_time = 0.0
        self.tts_engine = tts_engine

    # -----------------------------------------------------
    # SPEAK FUNCTION
    # -----------------------------------------------------

    def _speak(self, text):

        print(text)

        if self.tts_engine:
            try:
                self.tts_engine.speak(text)
            except Exception:
                pass

    # -----------------------------------------------------
    # READ FOCUSED ELEMENT
    # -----------------------------------------------------

    def _get_focused_element(self):

        try:
            element = uia_client.call("get_focus", timeout=0.4)
            if not isinstance(element, dict):
                return None
            role = element.get("control_type") or element.get("role") or "Element"
            name = element.get("name") or "Unnamed element"

            if not name:
                name = "Unnamed element"

            return f"{role}: {name}"

        except Exception:

            return None

    # -----------------------------------------------------
    # MONITOR LOOP
    # -----------------------------------------------------

    def _monitor_loop(self):

        while self.running:

            element = self._get_focused_element()
            now = time.time()

            if (
                element
                and element != self.last_element
                and (now - self.last_spoken_time) >= 0.7
            ):

                self.last_element = element
                self.last_spoken_time = now

                self._speak(element)

            time.sleep(0.35)

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    def start(self):

        if self.running:
            return

        self.running = True

        thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )

        thread.start()

    # -----------------------------------------------------
    # STOP
    # -----------------------------------------------------

    def stop(self):

        self.running = False                                        
