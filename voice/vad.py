from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import webrtcvad


@dataclass
class VADDecision:
    is_speech: bool
    energy: float
    speech_confidence: float


class VAD:
    """
    Production VAD that combines WebRTC VAD with adaptive energy gating.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 3,
        min_energy: float = 0.008,
        adaptive_margin: float = 2.2,
    ):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad(aggressiveness)
        self.min_energy = min_energy
        self.adaptive_margin = adaptive_margin
        self.noise_floor = min_energy
        self._initialized = False

    def analyze(self, frame: bytes) -> VADDecision:
        if not frame:
            return VADDecision(is_speech=False, energy=0.0, speech_confidence=0.0)

        audio = np.frombuffer(frame, dtype=np.int16)
        if audio.size == 0:
            return VADDecision(is_speech=False, energy=0.0, speech_confidence=0.0)

        normalized = audio.astype(np.float32) / 32768.0
        energy = float(np.sqrt(np.mean(np.square(normalized))))

        try:
            webrtc_detected = self.vad.is_speech(frame, self.sample_rate)
        except Exception:
            webrtc_detected = False

        if not self._initialized:
            self.noise_floor = max(self.min_energy, energy)
            self._initialized = True
        elif not webrtc_detected:
            self.noise_floor = (self.noise_floor * 0.92) + (energy * 0.08)

        energy_threshold = max(self.min_energy, self.noise_floor * self.adaptive_margin)
        energy_detected = energy >= energy_threshold
        is_speech = bool(webrtc_detected and energy_detected)

        confidence = 0.0
        if energy_threshold > 0:
            confidence = min(1.0, energy / energy_threshold)
        if webrtc_detected:
            confidence = min(1.0, confidence + 0.15)

        return VADDecision(
            is_speech=is_speech,
            energy=round(energy, 5),
            speech_confidence=round(confidence, 3),
        )

    def is_speech(self, frame: bytes) -> bool:
        return self.analyze(frame).is_speech
