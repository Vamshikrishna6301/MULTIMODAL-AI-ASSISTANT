from execution.input.nvda_keymap import KEY_COMMANDS


class NVDACommandHandler:

    def __init__(self, router):

        self.router = router

    def handle_key(self, key):

        key_str = str(key)

        action = KEY_COMMANDS.get(key_str)

        if not action:
            return

        decision = {
            "status": "APPROVED",
            "action": action
        }

        response = self.router.route(decision)

        if response and response.spoken_message:
            print(response.spoken_message)