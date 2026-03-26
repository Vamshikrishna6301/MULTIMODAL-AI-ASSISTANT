from pathlib import Path

from faster_whisper import WhisperModel
import numpy as np
import threading
import re

from config_production import COMPUTE_CONFIG

try:
    import torch  # type: ignore
except ImportError:  # pragma: no cover
    torch = None


class STT:

    MODEL_NAME = "small.en"
    MODEL_DIR = Path("models") / "faster_whisper"

    def __init__(self):

        self._lock = threading.Lock()
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        gpu_available = bool(torch and torch.cuda.is_available())
        self.device = COMPUTE_CONFIG.get("whisper_device", "cuda")
        if self.device == "cuda" and not gpu_available:
            self.device = "cpu"

        compute_type = COMPUTE_CONFIG.get("whisper_compute_type", "float16")
        if self.device == "cpu":
            compute_type = "int8"

        print(f"Loading Whisper on {self.device.upper()}...")

        self.model = WhisperModel(
            self.MODEL_NAME,
            device=self.device,
            compute_type=compute_type,
            cpu_threads=4,
            num_workers=1,
            download_root=str(self.MODEL_DIR)
        )

        dummy_audio = np.zeros(16000, dtype=np.float32)
        list(self.model.transcribe(dummy_audio, beam_size=1))

        print(f"Whisper warmed up on {self.device.upper()}")

    # =====================================================

    def transcribe(self, audio_bytes: bytes, input_sample_rate: int) -> str:

        if not audio_bytes:
            return ""

        audio = np.frombuffer(audio_bytes, dtype=np.int16)

        if audio.size == 0:
            return ""

        audio = audio.astype(np.float32) / 32768.0

        if len(audio) < input_sample_rate * 0.4:
            return ""

        if np.max(np.abs(audio)) < 0.02:
            return ""

        MAX_AUDIO_SECONDS = 8
        max_samples = int(input_sample_rate * MAX_AUDIO_SECONDS)

        if len(audio) > max_samples:
            audio = audio[:max_samples]

        try:

            with self._lock:

                segments_generator, info = self.model.transcribe(
                    audio,
                    language="en",
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    vad_filter=False,
                    without_timestamps=True,
                    condition_on_previous_text=False
                )

                segments = list(segments_generator)

        except Exception as e:
            print(f"❌ STT inference error: {e}")
            return ""

        text = " ".join(seg.text for seg in segments).strip().lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)

        return text
