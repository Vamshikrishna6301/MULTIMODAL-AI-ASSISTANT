#!/usr/bin/env python3
"""
Debug startup to isolate where the application fails
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import traceback

print("=" * 60)
print("🔧 DEBUG STARTUP SEQUENCE")
print("=" * 60)

try:
    print("\n1️⃣  Importing voice.voice_loop...")
    from voice.voice_loop import VoiceLoop
    print("   ✅ voice_loop imported")
except Exception as e:
    print(f"   ❌ Failed to import voice_loop:")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n2️⃣  Creating VoiceLoop instance...")
    assistant = VoiceLoop()
    print("   ✅ VoiceLoop instance created")
except Exception as e:
    print(f"   ❌ Failed to create VoiceLoop:")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n3️⃣  Starting production mode...")
    assistant.start_production()
    print("   ✅ Production mode started")
except KeyboardInterrupt:
    print("\n   ⏸️  KeyboardInterrupt caught")
except Exception as e:
    print(f"   ❌ Failed during production:")
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Startup debug complete")
