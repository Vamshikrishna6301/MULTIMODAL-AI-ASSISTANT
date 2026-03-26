#!/usr/bin/env python3
"""
GPU-Optimized Multimodal Voice Assistant
Production entry point with CUDA support, logging, monitoring, and error handling
"""

# ============================================================
# CRITICAL: OPENMP + CUDA FIX
# ============================================================

import os
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent
ULTRALYTICS_DIR = PROJECT_ROOT / ".cache" / "ultralytics"
HF_HOME_DIR = PROJECT_ROOT / ".cache" / "huggingface"

ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
HF_HOME_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_DIR))
os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(ULTRALYTICS_DIR))
os.environ.setdefault("HF_HOME", str(HF_HOME_DIR))
os.environ.setdefault("TRANSFORMERS_CACHE", str(HF_HOME_DIR / "transformers"))

# ============================================================
# STANDARD IMPORTS
# ============================================================

import sys
import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# PRODUCTION INFRASTRUCTURE
# ============================================================

from config_production import (
    get_config,
    create_directories,
    AUDIO_CONFIG,
    VISION_CONFIG,
    COMPUTE_CONFIG,
    MONITORING_CONFIG,
)

from infrastructure.production_logger import get_production_logger
from infrastructure.system_monitor import (
    get_health_monitor,
    get_performance_tracker,
    get_resource_cleaner,
)
from infrastructure.runtime_recovery import RuntimeRecoveryManager

from infrastructure.error_handling import retry_with_backoff, RetryConfig

# ============================================================
# GLOBAL OBJECTS
# ============================================================

_logger = None
_health_monitor = None
_performance_tracker = None
_resource_cleaner = None
_recovery_manager = None

_focus_listener = None
_keyboard_nav = None
_navigator = None


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_production_infrastructure():

    global _logger, _health_monitor, _performance_tracker, _resource_cleaner, _recovery_manager

    print("\n" + "=" * 70)
    print("🚀 MULTIMODAL AI ACCESSIBILITY SYSTEM (PRODUCTION)")
    print("=" * 70 + "\n")

    print("📁 Creating directory structure...")
    create_directories()

    print("📝 Initializing production logging...")
    _logger = get_production_logger()
    app_logger = _logger.get_logger("main")

    app_logger.info("Application startup initiated")

    _recovery_manager = RuntimeRecoveryManager()
    last_state = _recovery_manager.get_last_runtime_state()
    if _recovery_manager.needs_recovery():
        app_logger.warning(
            "Previous runtime did not shut down cleanly",
            extra={"last_runtime_state": last_state},
        )
    _recovery_manager.mark_startup()

    print("💚 Starting health monitor...")
    _health_monitor = get_health_monitor()
    _health_monitor.start()

    print("⚡ Starting performance tracker...")
    _performance_tracker = get_performance_tracker()

    print("🧹 Starting resource cleaner...")
    _resource_cleaner = get_resource_cleaner()
    _recovery_manager.mark_ready()

    print()

    return app_logger


# ============================================================
# SYSTEM VERIFICATION
# ============================================================

@retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=1.0))
def verify_system_ready():

    try:
        import torch
    except Exception:
        print("Torch not available; continuing without GPU verification.")
        print()
        return False

    cuda_available = torch.cuda.is_available()

    print("📊 System Configuration:")

    print(f"   GPU Available: {'✅ Yes' if cuda_available else '❌ No'}")

    if cuda_available:

        print(f"   GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   PyTorch Version: {torch.__version__}")

    print()

    return cuda_available


# ============================================================
# ACCESSIBILITY INITIALIZATION
# ============================================================

def initialize_accessibility():

    global _focus_listener, _keyboard_nav, _navigator

    try:
        import comtypes.client

        comtypes.client.GetModule("UIAutomationCore.dll")
        from execution.accessibility.uia_focus_event_listener import UIFocusEventListener
        from execution.accessibility.accessibility_navigator import AccessibilityNavigator
        from execution.accessibility.keyboard_navigation import KeyboardNavigator
        from execution.accessibility.screen_reader_flag import enable_screen_reader_mode
        from voice.tts import TTS
    except Exception as exc:
        print(f"Accessibility initialization skipped: {exc}")
        return False

    print("♿ Enabling screen reader mode...")
    enable_screen_reader_mode()

    print("🧭 Initializing accessibility navigator...")
    _navigator = AccessibilityNavigator()

    tts = TTS()

    def speak(text):

        if not text:
            return

        print(text)  # debug log
        tts.speak(text)

    print("👁 Starting focus listener...")
    _focus_listener = UIFocusEventListener(
    speak,
    _navigator.state
)
    _focus_listener.start()

    print("⌨ Starting keyboard navigation...")
    _keyboard_nav = KeyboardNavigator(_navigator, speak)
    _keyboard_nav.start()

    print("✅ Accessibility system ready\n")
    return True


# ============================================================
# CLEAN SHUTDOWN
# ============================================================

def cleanup_on_shutdown():

    print("\n🛑 Shutting down application...\n")

    try:
        from execution.accessibility.uia_client import uia_client

        if _focus_listener:
            _focus_listener.stop()

        if _resource_cleaner:
            _resource_cleaner.cleanup_all()

        if _health_monitor:
            _health_monitor.stop()

        if _recovery_manager:
            _recovery_manager.mark_shutdown()

        uia_client.stop_worker()

        print("✅ Shutdown complete")

    except Exception as e:

        print(f"⚠️ Shutdown error: {e}")


def handle_signal(signum, frame):

    cleanup_on_shutdown()
    sys.exit(0)


# ============================================================
# MAIN ENTRY
# ============================================================

if __name__ == "__main__":

    try:

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        app_logger = initialize_production_infrastructure()

        verify_system_ready()

        config = get_config()

        app_logger.info(
            "Production constants loaded",
            extra={
                "audio_sample_rate": AUDIO_CONFIG["sample_rate"],
                "vision_resolution": VISION_CONFIG["resolution"],
                "compute_device": COMPUTE_CONFIG["whisper_device"],
                "monitoring_enabled": bool(MONITORING_CONFIG),
            },
        )

        # --------------------------------------------------
        # START ACCESSIBILITY SYSTEM
        # --------------------------------------------------

        accessibility_ready = initialize_accessibility()

        # --------------------------------------------------
        # START VOICE ASSISTANT
        # --------------------------------------------------

        print("🎤 Starting voice assistant...\n")

        try:
            from voice.voice_loop import VoiceLoop
            assistant = VoiceLoop()
            assistant.runtime.focus_listener = _focus_listener
            assistant.start_production()
        except Exception as exc:
            if app_logger:
                app_logger.warning(
                    "Voice stack unavailable, running in degraded mode",
                    extra={
                        "error": str(exc),
                        "accessibility_ready": accessibility_ready,
                    },
                )
            print(f"Voice assistant initialization skipped: {exc}")
            print("Service started in degraded mode.")

    except KeyboardInterrupt:

        cleanup_on_shutdown()

    except Exception as e:

        print(f"\n❌ Fatal error: {e}")

        cleanup_on_shutdown()
        sys.exit(1)                                                                                                                                                                                                                                                                                                                                                                                         
