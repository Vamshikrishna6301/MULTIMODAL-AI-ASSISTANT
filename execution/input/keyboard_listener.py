from pynput import keyboard


class KeyboardListener:

    def __init__(self, command_handler):

        self.command_handler = command_handler

    def on_press(self, key):

        try:
            k = key.char
        except AttributeError:
            k = key

        self.command_handler.handle_key(k)

    def start(self):

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()