import sounddevice as sd
import numpy as np

print("Recording 3 seconds...")

audio = sd.rec(
    int(3 * 48000),
    samplerate=48000,
    channels=1,
    dtype="int16"
)

sd.wait()

print("Recording complete.")

print("Mean amplitude:", np.abs(audio).mean())