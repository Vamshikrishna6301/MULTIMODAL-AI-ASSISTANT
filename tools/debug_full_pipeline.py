import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import threading
import traceback

from voice.voice_loop import VoiceLoop
from voice.assistant_runtime import AssistantRuntime


def banner(msg):
    print("\n" + "=" * 60)
    print(msg)
    print("=" * 60)


def trace(msg):
    print(f"[TRACE {time.strftime('%H:%M:%S')}] {msg}")


class DebugVoiceLoop(VoiceLoop):

    def _execution_worker(self):
        import pythoncom
        pythoncom.CoInitialize()

        banner("EXECUTION WORKER STARTED")

        try:
            while self.runtime.running:
                try:
                    trace("Waiting for command...")
                    decision_dict = self.command_queue.get(timeout=1)
                    trace(f"Command dequeued: {decision_dict}")

                except Exception:
                    continue

                response = None

                try:
                    trace("Calling router.route()")
                    start = time.time()

                    response = self.router.route(decision_dict)

                    elapsed = round(time.time() - start, 3)
                    trace(f"router.route() returned in {elapsed}s")

                except Exception:
                    print("ROUTER CRASH")
                    traceback.print_exc()
                    continue

                try:
                    trace("Processing response")

                    if response:
                        trace(f"Response object: {response}")
                        message = getattr(response, "spoken_message", None)
                        metadata = getattr(response, "metadata", {})

                        trace(f"Message: {message}")
                        trace(f"Metadata: {metadata}")

                        if message:
                            print("\nAssistant:", message)

                            if not metadata.get("suppress_tts") and not metadata.get("tts_handled"):
                                trace("Calling TTS.speak()")
                                self.tts.speak(message)
                                trace("TTS.speak() returned")
                        else:
                            trace("No message in response")

                    else:
                        trace("Response is None")

                except Exception:
                    print("RESPONSE PROCESSING CRASH")
                    traceback.print_exc()

        finally:
            pythoncom.CoUninitialize()


def run_debug():

    banner("VOICE ASSISTANT FULL PIPELINE DEBUG")

    runtime = AssistantRuntime()
    assistant = DebugVoiceLoop(runtime)

    banner("Starting worker threads")

    assistant._start_threads()

    while True:

        cmd = input("\nManual Command> ").strip()

        if cmd == "exit":
            break

        try:
            banner(f"Injecting command: {cmd}")

            decision = assistant.fusion.process_text(cmd)
            decision_dict = decision.to_dict()

            trace(f"Decision: {decision_dict}")

            assistant.command_queue.put(decision_dict)

        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    run_debug()