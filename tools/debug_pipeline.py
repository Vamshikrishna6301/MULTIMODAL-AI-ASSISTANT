import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import queue
import threading

from voice.voice_loop import VoiceLoop
from voice.assistant_runtime import AssistantRuntime


def banner(msg):
    print("\n" + "=" * 60)
    print(msg)
    print("=" * 60)


class TracedVoiceLoop(VoiceLoop):

    def _handle_intent(self, text: str):
        print("\n[INTENT WORKER] Processing:", text)

        decision = self.fusion.process_text(text)
        decision_dict = decision.to_dict()

        print("[INTENT WORKER] Decision:", decision_dict)

        status = decision_dict.get("status")

        if status == "APPROVED":
            print("[INTENT WORKER] Queue size before:", self.command_queue.qsize())

            try:
                self.command_queue.put(decision_dict, timeout=1)
                print("[INTENT WORKER] Command queued")

            except queue.Full:
                print("[INTENT WORKER] COMMAND QUEUE FULL")

        else:
            print("[INTENT WORKER] Not approved")


    def _execution_worker(self):
        import pythoncom
        pythoncom.CoInitialize()

        print("\n[EXECUTION WORKER] Started")

        try:
            while self.runtime.running:

                try:
                    decision_dict = self.command_queue.get(timeout=1)
                except queue.Empty:
                    continue

                print("\n[EXECUTION WORKER] Received:", decision_dict)

                response = self.router.route(decision_dict)

                print("[EXECUTION WORKER] Response:", response)

                if response and hasattr(response, "spoken_message"):
                    msg = response.spoken_message

                    print("Assistant:", msg)

                    if msg:
                        self.tts.speak(msg)

        finally:
            pythoncom.CoUninitialize()


def run():
    banner("VOICE PIPELINE TRACE")

    runtime = AssistantRuntime()
    assistant = TracedVoiceLoop(runtime)

    assistant._start_threads()

    while True:

        cmd = input("\nCommand> ")

        if cmd == "exit":
            break

        assistant.text_queue.put(cmd)


if __name__ == "__main__":
    run()