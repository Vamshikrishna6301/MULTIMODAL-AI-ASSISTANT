import subprocess
import threading
import queue
import time

from voice.audio_guard import AudioFeedbackGuard
from infrastructure.logger import get_logger


class TTS:

    def __init__(self, runtime=None, feedback_guard: AudioFeedbackGuard = None):
        self.logger = get_logger("voice.tts")

        self._runtime = runtime
        self._feedback_guard = feedback_guard

        self._queue = queue.Queue(maxsize=10)

        self._stop_event = threading.Event()

        self._current_process = None

        self._lock = threading.Lock()

        # speech deduplication
        self._last_spoken = None
        self._last_time = 0

        # start worker
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self._thread.start()

    # =====================================================

    def speak(self, text: str):

        if not text:
            return

        text = text.strip()

        # ---- Deduplicate speech ----
        if text == self._last_spoken:
            return

        # ---- Rate limit navigation spam ----
        now = time.time()

        if now - self._last_time < 0.25:
            return

        self._last_spoken = text
        self._last_time = now

        # ---- Interrupt current speech ----
        self.stop()

        try:
            self._queue.put_nowait(text)
            self.logger.debug("tts_queue_enqueue", speech_length=len(text))
        except queue.Full:
            pass

    # =====================================================

    def is_speaking(self):

        if self._runtime:
            return self._runtime.is_speaking()

        return False

    # =====================================================

    def _run_loop(self):

        while not self._stop_event.is_set():

            try:
                text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self._runtime and self._runtime.interrupted:
                self._runtime.clear_interrupt()
                continue

            if self._runtime:
                self._runtime.start_speaking()
                self._runtime.block_listening(0.8)

            if self._feedback_guard:
                self._feedback_guard.mark_tts_start(text)

            try:

                safe_text = (
                    text.replace('"', '')
                    .replace("`", "")
                    .replace("$", "")
                )
                self.logger.debug("tts_before_speak", speech_length=len(safe_text))

                command = (
                    'Add-Type -AssemblyName System.Speech; '
                    '$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    '$speak.Rate = 1; '
                    f'$speak.Speak("{safe_text}")'
                )

                with self._lock:

                    self._current_process = subprocess.Popen(
                        ["powershell", "-Command", command],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                while True:
                    with self._lock:
                        proc = self._current_process

                    if not proc:
                        break

                    if proc.poll() is not None:
                        break

                    if self._runtime and self._runtime.interrupted:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                        break

                    time.sleep(0.05)
                self.logger.debug("tts_after_speak", speech_length=len(safe_text))

            except Exception as exc:
                self.logger.error("tts_speak_failed", exception=exc)

            finally:

                with self._lock:
                    if self._current_process:
                        try:
                            self._current_process.kill()
                        except Exception:
                            pass
                    self._current_process = None

                if self._feedback_guard:
                    self._feedback_guard.mark_tts_end()

                if self._runtime:
                    self._runtime.stop_speaking()
                    self._runtime.block_listening(0.6)

    # =====================================================

    def stop(self):

        with self._lock:

            if (
                self._current_process
                and self._current_process.poll() is None
            ):
                try:
                    self._current_process.terminate()
                except Exception:
                    pass

                self._current_process = None

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        if self._runtime:
            self._runtime.stop_speaking()
            self._runtime.block_listening(0.3)

        if self._feedback_guard:
            self._feedback_guard.mark_tts_end()

    # =====================================================

    def shutdown(self):

        self.stop()

        self._stop_event.set()

        self._thread.join(timeout=2)
