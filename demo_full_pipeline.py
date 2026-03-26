"""
Demo runner for Phase 1 + 2 + 3 combined (safe dry-run).
Simulates STT transcripts and shows pipeline decisions and executor outputs.
"""
from voice.voice_loop import VoiceLoop
import time

SAMPLE_UTTERANCES = [
    "hey assistant",
    "open chrome",
    "type hello world",
    "delete C:/important.txt",
    "delete all files",
    "what time is it",
]


def run_demo():
    vl = VoiceLoop()
    # Prevent actual TTS audio; replace speak with print
    try:
        vl.tts.speak = lambda msg: print(f"[TTS] {msg}")
    except Exception:
        pass

    print("\n=== Running Phase 1+2+3 demo (dry-run) ===")
    for text in SAMPLE_UTTERANCES:
        print(f"\n-- Simulated STT: {text}")
        vl._handle_intent(text)
        time.sleep(0.25)

    print("\n✅ Demo complete")

if __name__ == '__main__':
    run_demo()
