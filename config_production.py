"""
PRODUCTION CONFIGURATION
Centralized settings for production deployment
"""
import os
from pathlib import Path
from typing import Dict, Any

# ============================================================
# ENVIRONMENT
# ============================================================

ENVIRONMENT = os.getenv("ENV", "production")  # development, staging, production
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / ".cache"

# ============================================================
# AUDIO CONFIGURATION
# ============================================================

AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration_ms": 30,
    "vad_aggressiveness": 3,  # 0-3, higher = more aggressive
    "max_silence_frames": 20,
    "buffer_size": 16384,  # Larger buffer for stability
}

# ============================================================
# VISION CONFIGURATION
# ============================================================

VISION_CONFIG = {
    "camera_device": 0,
    "resolution": (640, 480),
    "fps": 30,
    "detector_model": "yolov8m.pt",
    "detection_confidence": 0.3,
    "stabilization_buffer_size": 5,
    "stabilization_min_duration": 0.5,
    "enable_background_thread": True,
}

# ============================================================
# GPU/CPU CONFIGURATION
# ============================================================

COMPUTE_CONFIG = {
    "gpu_enabled": True,
    "gpu_device": 0,
    "cuda_visible_devices": "0",
    "whisper_device": "cuda",  # cuda or cpu
    "whisper_compute_type": "float16",  # float32, float16, int8
    "whisper_batch_size": 1,
    "yolo_device": "cuda",
    "yolo_half_precision": False,
}

# ============================================================
# THREADING & CONCURRENCY
# ============================================================

THREADING_CONFIG = {
    "max_threads": 6,
    "voice_thread_priority": 5,  # Higher = more priority
    "vision_thread_priority": 3,
    "thread_timeout": 10,  # seconds
    "enable_thread_monitoring": True,
}

# ============================================================
# PERFORMANCE TUNING
# ============================================================

PERFORMANCE_CONFIG = {
    "enable_profiling": DEBUG_MODE,
    "enable_memory_optimization": True,
    "enable_lazy_loading": True,
    "cache_intent_patterns": True,
    "cache_detector_models": True,
    "preload_models": True,  # Load on startup vs on-demand
    "enable_response_cache": True,
    "response_cache_ttl_seconds": 1,
}

# ============================================================
# SAFETY & CONFIRMATION
# ============================================================

SAFETY_CONFIG = {
    "confirmation_timeout": 30,  # seconds
    "max_confirmation_attempts": 3,
    "require_confirmation_for_high_risk": True,
    "min_confidence_for_execution": 0.70,
    "safety_log_all_actions": True,
}

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

LOGGING_CONFIG = {
    "level": "DEBUG" if DEBUG_MODE else "INFO",
    "format": "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
    "max_bytes": 10_485_760,  # 10 MB
    "backup_count": 5,
    "log_file": LOG_DIR / "assistant.log",
    "error_file": LOG_DIR / "errors.log",
    "console_output": True,
}

# ============================================================
# MONITORING & HEALTH CHECKS
# ============================================================

MONITORING_CONFIG = {
    "enable_health_checks": True,
    "health_check_interval": 30,  # seconds
    "enable_metrics": True,
    "metrics_update_interval": 5,  # seconds
    "enable_memory_monitoring": True,
    "memory_threshold_percent": 80,  # Alert if > 80% usage
    "enable_gpu_monitoring": True,
    "enable_watchdog": True,
    "watchdog_timeout_seconds": 15,
}

PLUGIN_CONFIG = {
    "plugins_dir": PROJECT_ROOT / "plugins",
    "autoload": True,
}

# ============================================================
# TIMEOUTS
# ============================================================

TIMEOUT_CONFIG = {
    "voice_capture": 300,  # 5 minutes max
    "speech_to_text": 60,  # 1 minute max
    "intent_parsing": 10,  # 10 seconds max
    "execution": 30,  # 30 seconds max
    "text_to_speech": 30,  # 30 seconds max
    "vision_frame_processing": 5,  # 5 seconds max
}

# ============================================================
# GRACEFUL DEGRADATION
# ============================================================

DEGRADATION_CONFIG = {
    "enable_fallback_tts": True,  # Fallback from pyttsx3 to silence
    "enable_cpu_stts": True,  # CPU fallback for STT
    "enable_basic_mode": True,  # Voice-only if vision fails
    "max_failures_before_fallback": 3,
}

# ============================================================
# INITIALIZATION
# ============================================================

def create_directories():
    """Create necessary directories."""
    for directory in [LOG_DIR, DATA_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_config() -> Dict[str, Any]:
    """Get all configuration as dictionary."""
    return {
        "audio": AUDIO_CONFIG,
        "vision": VISION_CONFIG,
        "compute": COMPUTE_CONFIG,
        "threading": THREADING_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "safety": SAFETY_CONFIG,
        "logging": LOGGING_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "plugins": PLUGIN_CONFIG,
        "timeouts": TIMEOUT_CONFIG,
        "degradation": DEGRADATION_CONFIG,
    }


# Initialize on import
create_directories()
