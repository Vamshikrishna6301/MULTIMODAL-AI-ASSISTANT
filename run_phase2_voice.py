import sys
import time

from core.fusion_engine import FusionEngine
from voice.stt import STT
from voice.tts import TTS
from voice.mic_stream import MicrophoneStream
from voice.vad import VAD


class VoicePhase2Assistant:

    def __init__(self):
        self.engine = FusionEngine()
        self.stt = STT()
        self.tts = TTS()
        self.vad = VAD()  # high aggressiveness inside VAD
        self.running = True

        # Silence control
        self.silence_threshold = 15        # frames of silence before stop
        self.max_record_seconds = 6        # max recording duration
        self.min_speech_frames = 4         # minimum speech frames (~240ms)

    # =====================================================

    def start(self):
        print("\n🎤 Phase 2 Assistant (Noise-Robust Mode)")
        print("Speak naturally. Say 'exit' to stop.\n")

        with MicrophoneStream() as mic:

            sample_rate = mic.get_sample_rate()

            try:
                while self.running:

                    audio_buffer = []
                    silence_counter = 0
                    speech_detected = False
                    speech_frames = 0
                    start_time = time.time()

                    # =========================
                    # Capture speech segment
                    # =========================
                    while True:
                        frame_bytes = mic.read()

                        try:
                            is_speech = self.vad.is_speech(frame_bytes)
                        except Exception:
                            continue  # skip bad frames safely

                        if is_speech:
                            speech_detected = True
                            silence_counter = 0
                            speech_frames += 1
                            audio_buffer.append(frame_bytes)
                        else:
                            if speech_detected:
                                silence_counter += 1
                                audio_buffer.append(frame_bytes)

                        # Stop after silence
                        if speech_detected and silence_counter > self.silence_threshold:
                            break

                        # Stop after max duration
                        if time.time() - start_time > self.max_record_seconds:
                            break

                    # =========================
                    # Filter very short speech
                    # =========================
                    if speech_frames < self.min_speech_frames:
                        continue

                    if not audio_buffer:
                        continue

                    audio_bytes = b"".join(audio_buffer)

                    # =========================
                    # Transcribe
                    # =========================
                    text = self.stt.transcribe(audio_bytes, sample_rate)

                    if not text:
                        continue

                    text = text.strip().lower()

                    # Ignore very short noise transcripts
                    

                    # Ignore obvious noise words only
                    noise_words = {"uh", "um", "hmm"}

                    if text in noise_words:
                        continue

                    print(f"\n🗣 You said: {text}")

                    if "exit" in text:
                        self._shutdown()
                        break

                    # =========================
                    # Process through engine
                    # =========================
                    decision = self.engine.process_text(text)

                    if decision is None:
                        print("⏳ Waiting for confirmation...")
                        self.tts.speak("Please say yes or no.")
                        continue

                    self._handle_decision(decision)

            except KeyboardInterrupt:
                self._shutdown()
                sys.exit(0)

    # =====================================================

    def _handle_decision(self, decision):

        if hasattr(decision, "to_dict"):
            data = decision.to_dict()
        else:
            print("Unexpected decision type:", type(decision))
            return

        print("Decision:", data)

        message = data.get("message")

        if message:
            self.tts.speak(message)

    # =====================================================

    def _shutdown(self):
        print("👋 Shutting down.")
        self.tts.speak("Goodbye.")
        self.running = False


if __name__ == "__main__":
    assistant = VoicePhase2Assistant()
    assistant.start()