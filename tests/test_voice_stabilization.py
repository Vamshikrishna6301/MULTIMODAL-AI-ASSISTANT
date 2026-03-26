import time

from voice.audio_guard import AudioFeedbackGuard
from voice.vad import VAD


def _frame(amplitude: int, samples: int = 480) -> bytes:
    sample = int(max(-32768, min(32767, amplitude)))
    return (sample.to_bytes(2, byteorder="little", signed=True)) * samples


def test_audio_feedback_guard_blocks_recent_tts_capture():
    guard = AudioFeedbackGuard(
        echo_window_seconds=2.0,
        post_speech_suppression_seconds=0.2,
        similarity_threshold=0.8,
    )

    guard.mark_tts_start("Opening Chrome now")
    assert guard.is_capture_blocked() is True
    assert guard.should_suppress_transcript("opening chrome now") is True


def test_audio_feedback_guard_allows_unrelated_text_after_window():
    guard = AudioFeedbackGuard(
        echo_window_seconds=0.1,
        post_speech_suppression_seconds=0.05,
        similarity_threshold=0.9,
    )

    guard.mark_tts_start("Done")
    guard.mark_tts_end()
    time.sleep(0.12)

    assert guard.is_capture_blocked() is False
    assert guard.should_suppress_transcript("open notepad") is False


def test_vad_rejects_low_energy_noise():
    vad = VAD(min_energy=0.01, adaptive_margin=2.0)

    quiet = _frame(30)
    decision = vad.analyze(quiet)

    assert decision.is_speech is False
    assert decision.energy < 0.01


def test_vad_accepts_high_energy_voice_like_frame():
    vad = VAD(min_energy=0.004, adaptive_margin=1.4)

    _ = vad.analyze(_frame(40))
    strong = _frame(6000)
    decision = vad.analyze(strong)

    assert decision.energy > 0.05
    assert decision.speech_confidence > 0.5
