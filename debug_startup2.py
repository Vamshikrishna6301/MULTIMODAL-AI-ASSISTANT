#!/usr/bin/env python3
"""
Enhanced debug startup to test all components
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import traceback
import threading
import time

print("=" * 70)
print("🔧 ENHANCED DEBUG STARTUP - COMPONENT TESTING")
print("=" * 70)

# Test 1: STT
print("\n[TEST 1] Testing STT initialization...")
try:
    from voice.stt import STT
    stt = STT()
    print(f"✅ STT initialized in {stt.device_mode} mode")
except Exception as e:
    print(f"❌ STT failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: VAD
print("\n[TEST 2] Testing VAD initialization...")
try:
    from voice.vad import VAD
    vad = VAD()
    print("✅ VAD initialized")
except Exception as e:
    print(f"❌ VAD failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: TTS
print("\n[TEST 3] Testing TTS initialization...")
try:
    from voice.assistant_runtime import AssistantRuntime
    from voice.tts import TTS
    runtime = AssistantRuntime()
    tts = TTS(runtime=runtime)
    print("✅ TTS initialized")
except Exception as e:
    print(f"❌ TTS failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 4: Full VoiceLoop
print("\n[TEST 4] Testing full VoiceLoop...")
try:
    from voice.voice_loop import VoiceLoop
    print("  Creating VoiceLoop instance...")
    assistant = VoiceLoop()
    print("  ✅ VoiceLoop instance created")
except Exception as e:
    print(f"  ❌ VoiceLoop failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 5: Start with timeout
print("\n[TEST 5] Starting production mode (10 second timeout)...")
print("  (Waiting for audio or 10 seconds to elapse)\n")

def timeout_handler():
    time.sleep(10)
    print("\n⏰ Timeout reached - stopping...")
    assistant.runtime.stop()

timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
timeout_thread.start()

try:
    assistant.start_production()
except KeyboardInterrupt:
    print("\n   ✋  KeyboardInterrupt (expected)")
except Exception as e:
    print(f"\n❌ Production failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS COMPLETED")
print("=" * 70)
