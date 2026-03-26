from __future__ import annotations

import re
import threading
import time
from collections import deque
from difflib import SequenceMatcher
from typing import Deque, Optional, Tuple


class AudioFeedbackGuard:
    """
    Prevents TTS-to-STT feedback loops by:
    - blocking microphone capture for a short post-TTS window
    - suppressing transcripts that closely match recent assistant speech
    """

    def __init__(
        self,
        *,
        echo_window_seconds: float = 3.0,
        post_speech_suppression_seconds: float = 0.8,
        similarity_threshold: float = 0.82,
        history_size: int = 6,
    ):
        self.echo_window_seconds = echo_window_seconds
        self.post_speech_suppression_seconds = post_speech_suppression_seconds
        self.similarity_threshold = similarity_threshold
        self._history: Deque[Tuple[float, str]] = deque(maxlen=history_size)
        self._blocked_until = 0.0
        self._lock = threading.RLock()

    def mark_tts_start(self, text: str) -> None:
        normalized = self._normalize(text)
        if not normalized:
            return
        with self._lock:
            now = time.monotonic()
            self._history.append((now, normalized))
            self._blocked_until = max(
                self._blocked_until,
                now + self.post_speech_suppression_seconds,
            )

    def mark_tts_end(self) -> None:
        with self._lock:
            self._blocked_until = max(
                self._blocked_until,
                time.monotonic() + self.post_speech_suppression_seconds,
            )

    def is_capture_blocked(self) -> bool:
        with self._lock:
            return time.monotonic() < self._blocked_until

    def should_suppress_transcript(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return True

        with self._lock:
            now = time.monotonic()
            while self._history and (now - self._history[0][0]) > self.echo_window_seconds:
                self._history.popleft()

            if now < self._blocked_until:
                return True

            for _, spoken in self._history:
                if normalized == spoken:
                    return True
                similarity = SequenceMatcher(None, normalized, spoken).ratio()
                if similarity >= self.similarity_threshold:
                    return True

        return False

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._blocked_until = 0.0

    def _normalize(self, text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = text.lower().strip()
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
