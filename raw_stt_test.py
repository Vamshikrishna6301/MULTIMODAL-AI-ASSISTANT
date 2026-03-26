import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
DURATION = 4  # record 4 seconds

print("Loading model...")
model = WhisperModel("base.en", device="cuda", compute_type="float16")

print("Speak clearly after recording starts...")
audio = sd.rec(int(DURATION * SAMPLE_RATE),
               samplerate=SAMPLE_RATE,
               channels=1,
               dtype="int16")

sd.wait()

audio = audio.flatten().astype(np.float32) / 32768.0

segments, _ = model.transcribe(audio, language="en")

text = " ".join(seg.text for seg in segments)

print("\nRecognized:", text)