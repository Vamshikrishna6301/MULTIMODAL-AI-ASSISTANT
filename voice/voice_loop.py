from __future__ import annotations

import collections
import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Deque, Optional

from config import MAX_SILENCE_FRAMES
from core.fusion_engine import FusionEngine
from router.decision_router import DecisionRouter
from voice.assistant_runtime import AssistantRuntime
from voice.audio_guard import AudioFeedbackGuard
from voice.mic_stream import MicrophoneStream
from voice.stt import STT
from voice.tts import TTS
from voice.vad import VAD, VADDecision
from infrastructure.logger import get_logger


@dataclass
class AudioSegment:
    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    speech_frames: int
    mean_confidence: float


class VoiceLoop:
    """
    Production voice loop with:
    - TTS/STT feedback suppression
    - adaptive VAD segmentation
    - interrupt-safe TTS cancellation
    """

    MIN_SPEECH_FRAMES = 5
    MAX_SEGMENT_SECONDS = 8.0
    PRE_ROLL_FRAMES = 6
    POST_ROLL_FRAMES = 8
    MIN_TRANSCRIPT_CHARS = 2

    def __init__(self, runtime: AssistantRuntime = None):
        print("Initializing Voice Assistant components...")
        self.logger = get_logger("voice.loop")

        self.runtime = runtime or AssistantRuntime()
        self.feedback_guard = AudioFeedbackGuard()
        self.vad = VAD()
        self.stt = STT()
        self.tts = TTS(runtime=self.runtime, feedback_guard=self.feedback_guard)
        self.fusion = FusionEngine()
        self.router = DecisionRouter(self.fusion.memory)
        self.router.execution_engine.dispatcher.vision_executor.set_tts(self.tts)
        self.router.execution_engine.navigator.runtime = self.runtime

        self.audio_queue: "queue.Queue[AudioSegment]" = queue.Queue(maxsize=8)
        self.text_queue: "queue.Queue[str]" = queue.Queue(maxsize=16)
        self.command_queue: "queue.Queue[dict]" = queue.Queue(maxsize=32)
        self.pre_roll_buffer: Deque[bytes] = collections.deque(maxlen=self.PRE_ROLL_FRAMES)
        self.capture_buffer: Deque[bytes] = collections.deque()
        self.speech_confidences: Deque[float] = collections.deque()
        self.silence_frames = 0
        self.speech_frames = 0
        self.trailing_frames = 0
        self.segment_start_time: Optional[float] = None
        self._threads = []

    def start_production(self):
        print("\nPRODUCTION VOICE ASSISTANT STARTED\n")
        if self.runtime.focus_listener is not None:
            try:
                self.runtime.focus_listener.runtime = self.runtime
                if getattr(self.runtime.focus_listener, "handler", None) is not None:
                    self.runtime.focus_listener.handler.runtime = self.runtime
            except Exception:
                pass
        self._start_threads()

        try:
            while self.runtime.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.runtime.stop()
        finally:
            self.tts.shutdown()

        for worker in self._threads:
            worker.join(timeout=2)

    def _start_threads(self):
        for worker in (self._mic_worker, self._stt_worker, self._intent_worker, self._execution_worker):
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            self._threads.append(thread)

    def _mic_worker(self):
        try:
            with MicrophoneStream() as mic:
                sample_rate = mic.get_sample_rate()
                while self.runtime.running:
                    if self.runtime.is_listening_blocked() or self.feedback_guard.is_capture_blocked():
                        self._reset_capture_state(drop_preroll=False)
                        time.sleep(0.03)
                        continue

                    frame = mic.read()
                    if not frame:
                        continue

                    decision = self.vad.analyze(frame)
                    self._process_frame(frame, decision, sample_rate)
        except Exception as exc:
            print("Mic worker crashed:", exc)
            self.runtime.stop()

    def _process_frame(self, frame: bytes, decision: VADDecision, sample_rate: int):
        if not self.capture_buffer:
            self.pre_roll_buffer.append(frame)

        if decision.is_speech:
            if not self.capture_buffer:
                self.capture_buffer.extend(self.pre_roll_buffer)
                self.pre_roll_buffer.clear()
                self.segment_start_time = time.monotonic()

            self.capture_buffer.append(frame)
            self.speech_confidences.append(decision.speech_confidence)
            self.speech_frames += 1
            self.trailing_frames = self.POST_ROLL_FRAMES
            self.silence_frames = 0
            self.runtime.mark_user_activity()
            return

        if not self.capture_buffer:
            return

        self.capture_buffer.append(frame)
        self.silence_frames += 1

        if self.trailing_frames > 0:
            self.trailing_frames -= 1

        segment_age = 0.0
        if self.segment_start_time:
            segment_age = time.monotonic() - self.segment_start_time

        if (
            self.silence_frames >= MAX_SILENCE_FRAMES
            and self.trailing_frames <= 0
        ) or segment_age >= self.MAX_SEGMENT_SECONDS:
            self._finalize_segment(sample_rate)

    def _finalize_segment(self, sample_rate: int):
        if not self.capture_buffer:
            self._reset_capture_state()
            return

        duration_seconds = len(self.capture_buffer) * 0.03
        mean_confidence = (
            sum(self.speech_confidences) / len(self.speech_confidences)
            if self.speech_confidences
            else 0.0
        )

        if self.speech_frames < self.MIN_SPEECH_FRAMES or duration_seconds < 0.35:
            self._reset_capture_state()
            return

        segment = AudioSegment(
            audio_bytes=b"".join(self.capture_buffer),
            sample_rate=sample_rate,
            duration_seconds=round(duration_seconds, 2),
            speech_frames=self.speech_frames,
            mean_confidence=round(mean_confidence, 3),
        )

        try:
            self.audio_queue.put(segment, timeout=0.2)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.audio_queue.put_nowait(segment)
            except queue.Full:
                pass

        self._reset_capture_state()

    def _reset_capture_state(self, *, drop_preroll: bool = True):
        self.capture_buffer.clear()
        self.speech_confidences.clear()
        self.silence_frames = 0
        self.speech_frames = 0
        self.trailing_frames = 0
        self.segment_start_time = None
        if drop_preroll:
            self.pre_roll_buffer.clear()

    def _stt_worker(self):
        while self.runtime.running:
            try:
                try:
                    segment = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                if self.runtime.is_executing():
                    continue

                while (
                    self.runtime.is_speaking()
                    or self.runtime.is_listening_blocked()
                ):
                    time.sleep(0.05)

                text = self.stt.transcribe(segment.audio_bytes, segment.sample_rate)
                if not text:
                    continue

                normalized = self._normalize(text)
                if not normalized or len(normalized) < self.MIN_TRANSCRIPT_CHARS:
                    continue

                if self.feedback_guard.should_suppress_transcript(normalized):
                    continue

                if normalized == getattr(self, "_last_transcript", None):
                    continue

                self._last_transcript = normalized

                print(f"[PIPELINE] STT text: {normalized}")
                print(f"\nHeard: {normalized}")
                self.text_queue.put(normalized)
            except Exception as exc:
                print("STT worker crashed:", exc)

    def _intent_worker(self):
        import pythoncom

        pythoncom.CoInitialize()
        try:
            while self.runtime.running:
                try:
                    text = self.text_queue.get(timeout=1)
                except queue.Empty:
                    continue

                clean_text = self._normalize(text)
                if self._is_noise_transcript(clean_text):
                    continue

                if self._is_exit_command(clean_text):
                    self.tts.stop()
                    self.tts.speak("Shutting down assistant.")
                    self.runtime.stop()
                    return

                if self._is_stop_command(clean_text):
                    self.runtime.request_interrupt()
                    self.tts.stop()
                    self._drain_audio_queue()
                    self._reset_capture_state()
                    continue

                if clean_text in {"thank you", "thanks"}:
                    self.tts.speak("You're welcome.")
                    continue

                decision = self.fusion.process_text(clean_text)
                if (
                    decision.status == "APPROVED"
                    and decision.intent
                    and getattr(decision.intent, "confirmed", False)
                ):
                    self._enqueue_command(decision.to_dict(), clean_text)
                    continue

                self._handle_intent(clean_text, decision=decision)
        finally:
            pythoncom.CoUninitialize()

    def _handle_intent(self, text: str, decision=None):
        if decision is None:
            decision = self.fusion.process_text(text)
        decision_dict = decision.to_dict()
        status = decision_dict.get("status")
        message = decision_dict.get("message")

        print(f"[PIPELINE] fusion decision: {decision_dict}")
        print(f"Decision Status: {status}")

        if status == "BLOCKED":
            if decision_dict.get("action") == "UNKNOWN":
                return
            if message == "Low confidence input":
                return
            self.tts.speak(message or "Action blocked.")
            return

        if status == "NEEDS_CONFIRMATION":
            self.runtime.set_confirmation(decision_dict)
            self.tts.speak(message or "Please confirm.")
            return

        if status == "APPROVED":
            try:
                if self.runtime.is_executing():
                    print("[PIPELINE] assistant busy, ignoring command")
                    return

                queue_size = self.command_queue.qsize()
                queue_capacity = self.command_queue.maxsize
                if queue_capacity > 0 and queue_size >= queue_capacity:
                    print(
                        f"[PIPELINE] command_queue full before put: size={queue_size} capacity={queue_capacity}"
                    )
                else:
                    print(
                        f"[PIPELINE] command_queue enqueue pending: size={queue_size} capacity={queue_capacity}"
                    )

                self._enqueue_command(decision_dict, text)
            except Exception as exc:
                print(f"[PIPELINE] command_queue enqueue failed: {exc!r}")
                self.tts.speak("Assistant is busy. Please try again.")

    def _execution_worker(self):
        import pythoncom

        pythoncom.CoInitialize()

        try:
            while self.runtime.running:
                try:
                    try:
                        decision_dict = self.command_queue.get(timeout=1)
                    except queue.Empty:
                        continue

                    print(
                        f"[PIPELINE] execution dequeued: {decision_dict} queue_size={self.command_queue.qsize()}"
                    )
                    response = None

                    self.runtime.start_execution()
                    try:
                        self.logger.debug(
                            "voice_execution_start",
                            action=decision_dict.get("action"),
                        )
                        print(
                            "[PIPELINE] execution start:",
                            {
                                "action": decision_dict.get("action"),
                                "runtime_state": str(self.runtime.get_state()),
                                "is_speaking": self.runtime.is_speaking(),
                                "listening_blocked": self.runtime.is_listening_blocked(),
                            },
                        )

                        response = self.router.route(decision_dict)
                        print(f"[PIPELINE] router response: {response}")

                        self.logger.debug(
                            "voice_execution_end",
                            action=decision_dict.get("action"),
                            success=getattr(response, "success", False),
                        )

                    finally:
                        self.runtime.finish_execution()

                    # --- Deliver output ---
                    if response and hasattr(response, "spoken_message"):
                        message = response.spoken_message

                        if message:
                            print(f"Assistant: {message}")
                            print(f"[PIPELINE] speaking: {message}")

                            metadata = getattr(response, "metadata", {}) or {}
                            print(f"[PIPELINE] response metadata: {metadata}")

                            if (
                                not metadata.get("suppress_tts")
                                and not metadata.get("tts_handled")
                            ):
                                self.tts.speak(message)
                    else:
                        print("[PIPELINE] speaking: Done.")
                        self.tts.speak("Done.")

                except Exception as exc:
                    print(f"[PIPELINE] execution worker exception: {exc!r}")
                    self.logger.error("voice_execution_failed", exception=exc)
                    self.tts.speak("Execution failed.")

        finally:
            pythoncom.CoUninitialize()

    def _drain_audio_queue(self):
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def _enqueue_command(self, decision_dict: dict, text: str) -> None:
        if self.runtime.is_executing():
            print("[PIPELINE] assistant busy, ignoring command")
            return

        if self.command_queue.qsize() > 0:
            print("[PIPELINE] execution pending, dropping command")
            self.logger.warning(
                "voice_command_dropped_execution_pending",
                action=decision_dict.get("action"),
                text=text,
            )
            return

        try:
            self.command_queue.put_nowait(decision_dict)
            print(
                f"[PIPELINE] intent queued: {decision_dict} queue_size={self.command_queue.qsize()}"
            )
            self.logger.debug(
                "voice_command_enqueued",
                action=decision_dict.get("action"),
                text=text,
            )
        except queue.Full:
            print("[PIPELINE] command_queue full, dropping command")
            self.logger.warning(
                "voice_command_dropped_queue_full",
                action=decision_dict.get("action"),
                text=text,
            )

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_noise_transcript(self, text: str) -> bool:
        if not text:
            return True
        if len(text.split()) == 1 and len(text) < 4:
            return True
        if len(text.split()) <= 2 and len(text) < 6:
            return True
        if text in {"uh", "um", "hmm", "mm", "ah"}:
            return True
        return False

    def _is_stop_command(self, text: str) -> bool:
        return text in {"stop", "cancel", "abort"}

    def _is_exit_command(self, text: str) -> bool:
        exit_phrases = {
            "exit",
            "quit",
            "shutdown assistant",
            "exit assistant",
            "close assistant",
            "stop assistant"
        }

        return text in exit_phrases
