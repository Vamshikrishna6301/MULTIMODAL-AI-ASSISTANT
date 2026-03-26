import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

device_id = 15
device_info = sd.query_devices(device_id)
native_sr = int(device_info["default_samplerate"])

print("Using sample rate:", native_sr)

model = WhisperModel("small.en", device="cuda", compute_type="float16")

print("Speak now...")

audio = sd.rec(
    int(4 * native_sr),
    samplerate=native_sr,
    channels=1,
    dtype="int16",
    device=device_id
)

sd.wait()

audio = audio.flatten().astype(np.float32) / 32768.0

segments, _ = model.transcribe(audio, language="en")

text = " ".join(seg.text for seg in segments)

print("Recognized:", text)