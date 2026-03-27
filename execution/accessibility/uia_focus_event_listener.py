import threading
import time

import comtypes
import pythoncom
from comtypes import GUID, client
from comtypes.gen.UIAutomationClient import (
    IUIAutomation,
    IUIAutomationFocusChangedEventHandler,
    UIA_NamePropertyId,
)

CUIAutomation = GUID("{FF48DBA4-60EF-4201-AA87-54103EEF594E}")


class FocusChangedEventHandler(comtypes.COMObject):

    _com_interfaces_ = [IUIAutomationFocusChangedEventHandler]

    def __init__(self, speak_callback, navigation_state, runtime=None):

        super().__init__()

        self.speak_callback = speak_callback
        self.navigation_state = navigation_state
        self.runtime = runtime

        self.last_focus_text = None
        self.last_spoken_time = 0.0

        self.cooldown = 0.7

        self.ignore_roles = {
            "pane",
            "group",
            "document",
            "custom",
            "pop-up",
            "popup",
        }
        self.ignore_names = {
            "file",
            "edit",
            "view",
            "help",
            "pane",
            "group",
        }

    def HandleFocusChangedEvent(self, sender):
        try:
            name = sender.GetCurrentPropertyValue(UIA_NamePropertyId)

            if not name:
                return 0

            name = str(name).strip()

            if not name:
                return 0

            now = time.time()

            if now - self.last_spoken_time < self.cooldown:
                return 0

            if name.lower() in self.ignore_names:
                return 0

            if name.lower() in self.ignore_roles:
                return 0

            if name == self.last_focus_text:
                return 0

            self.last_focus_text = name
            self.last_spoken_time = now

            from execution.accessibility.accessibility_navigator import UIElementWrapper

            wrapped = UIElementWrapper(sender, -1)

            try:
                self.navigation_state.set_focused(wrapped)
            except Exception:
                pass

            if self.runtime is not None and self.runtime.is_executing():
                return 0

            self.speak_callback(f"Focused: {name}")

        except Exception:
            pass

        return 0


class UIFocusEventListener:

    def __init__(self, speak_callback, navigation_state, runtime=None):

        self.speak_callback = speak_callback
        self.navigation_state = navigation_state
        self.runtime = runtime
        self._paused = False

        self.automation = None

        self.handler = FocusChangedEventHandler(
            self.speak_callback,
            self.navigation_state,
            self.runtime,
        )
        self.running = False

    def start(self):

        if self.running:
            return

        self.running = True

        def run():
            pythoncom.CoInitialize()

            try:
                automation = client.CreateObject(
                    CUIAutomation,
                    interface=IUIAutomation,
                )
                self.automation = automation

                automation.AddFocusChangedEventHandler(
                    None,
                    self.handler,
                )

                while self.running:
                    try:
                        if self._paused:
                            time.sleep(0.1)
                            continue

                        start = time.time()
                        pythoncom.PumpWaitingMessages()
                        if time.time() - start > 1.0:
                            pass
                        time.sleep(0.05)
                    except Exception as e:
                        time.sleep(0.3)
            finally:
                try:
                    if self.automation is not None:
                        self.automation.RemoveFocusChangedEventHandler(self.handler)
                except Exception:
                    pass
                self.automation = None
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):

        self.running = False
        self._paused = False

        try:
            if self.automation is not None:
                self.automation.RemoveFocusChangedEventHandler(self.handler)
        except Exception:
            pass
