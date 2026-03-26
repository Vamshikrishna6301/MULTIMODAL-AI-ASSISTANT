import socket
import json

HOST = "127.0.0.1"
PORT = 56789


class UIAClient:

    def _send(self, payload):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.send(json.dumps(payload).encode())
                response = s.recv(8192).decode()
                return json.loads(response)
        except Exception as e:
            return {
                "status": "error",
                "message": "UI automation service unavailable"
            }

    # -------------------------

    def read_screen(self):
        return self._send({"action": "read_screen"})

    def click_index(self, index):
        return self._send({
            "action": "click_index",
            "index": index
        })

    def click_by_name(self, name):
        return self._send({
            "action": "click_by_name",
            "name": name
        })
