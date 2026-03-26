import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import time

print("Loading model...")
model = WhisperModel("small.en", device="cuda", compute_type="float16")

sample_rate = 16000
duration = 4

print("Speak clearly after recording starts...")
time.sleep(1)

audio = sd.rec(int(sample_rate * duration),
               samplerate=sample_rate,
               channels=1,
               dtype="int16")

sd.wait()

audio = audio.flatten().astype(np.float32) / 32768.0

print("Transcribing...")

segments, _ = model.transcribe(
    audio,
    language="en",
    beam_size=1,
    temperature=0.0
)

text = " ".join(seg.text for seg in segments)

print("Recognized:", text)