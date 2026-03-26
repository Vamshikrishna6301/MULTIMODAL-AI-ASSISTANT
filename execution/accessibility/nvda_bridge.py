import win32gui
from pywinauto import Application
from pywinauto.keyboard import send_keys


class NVDABridge:

    def __init__(self):
        self.current_elements = []
        self.current_index = 0

    def _get_active_window(self):

        hwnd = win32gui.GetForegroundWindow()

        app = Application(backend="uia").connect(handle=hwnd)

        return app.window(handle=hwnd)

    def read_screen(self):

        window = self._get_active_window()

        elements = window.descendants()

        important = []

        for el in elements:

            try:
                name = el.window_text()
                role = el.friendly_class_name()

                if role in ["Button", "Edit", "Hyperlink", "Text", "MenuItem"]:

                    if name:
                        important.append({
                            "type": role,
                            "name": name,
                            "element": el
                        })

            except:
                pass

        self.current_elements = important
        self.current_index = 0

        readable = []

        for item in important[:15]:
            readable.append(f"{item['type']} : {item['name']}")

        return readable

    def next_item(self):

        if not self.current_elements:
            return "No elements loaded"

        self.current_index += 1

        if self.current_index >= len(self.current_elements):
            self.current_index = 0

        item = self.current_elements[self.current_index]

        return f"{item['type']} : {item['name']}"

    def activate(self):

        if not self.current_elements:
            return "No element selected"

        element = self.current_elements[self.current_index]["element"]

        try:
            element.click_input()
            return "Activated"
        except:
            return "Activation failed"

    def focus_input(self):

        send_keys("{TAB}")