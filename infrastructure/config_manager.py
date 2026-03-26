"""
Production-Grade Configuration Management
Environment-based configuration with validation and defaults
"""

import os
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class AudioConfig:
    """Audio capture configuration"""
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 30
    max_silence_frames: int = 20
    vad_aggressiveness: int = 3
    chunk_size: int = 2048


@dataclass
class STTConfig:
    """Speech-to-Text configuration"""
    model_name: str = "base"
    use_gpu: bool = True
    device: str = "cuda"
    beam_size: int = 5
    best_of: int = 5
    language: str = "en"


@dataclass
class TTSConfig:
    """Text-to-Speech configuration"""
    engine: str = "pyttsx3"
    rate: int = 150
    volume: int = 1.0


@dataclass
class SafetyConfig:
    """Safety engine configuration"""
    require_confirmation_threshold: float = 0.6
    min_confidence: float = 0.3
    dangerous_actions_require_confirmation: bool = True
    block_extreme_risk: bool = True
    extreme_risk_level: int = 9


@dataclass
class ExecutionConfig:
    """Execution engine configuration"""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 60.0


@dataclass
class CacheConfig:
    """Caching configuration"""
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 100


@dataclass
class LoggingConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    error_log_file: str = "logs/errors.log"
    json_log_file: str = "logs/app.json.log"
    enable_console_output: bool = True
    enable_file_output: bool = True


@dataclass
class APIConfig:
    """REST API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    enable_swagger: bool = True
    api_version: str = "v1"


@dataclass
class PersistenceConfig:
    """Database and persistence configuration"""
    db_type: str = "sqlite"  # sqlite, postgresql, mongodb
    db_path: str = "data/assistant.db"
    enable_history: bool = True
    history_retention_days: int = 90
    enable_session_persistence: bool = True


class ConfigManager:
    """
    Centralized configuration management
    - Loads from environment variables
    - Supports multiple environments
    - Provides defaults
    - Validates configuration
    """

    def __init__(self, env: Optional[str] = None):
        self.environment = Environment(
            env or os.getenv("APP_ENV", "development")
        )
        
        # Initialize all configs
        self.audio = AudioConfig(
            sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", 16000)),
            channels=int(os.getenv("AUDIO_CHANNELS", 1)),
            frame_duration_ms=int(os.getenv("AUDIO_FRAME_DURATION_MS", 30)),
            max_silence_frames=int(os.getenv("MAX_SILENCE_FRAMES", 20)),
            vad_aggressiveness=int(os.getenv("VAD_AGGRESSIVENESS", 3)),
        )
        
        self.stt = STTConfig(
            model_name=os.getenv("STT_MODEL", "base"),
            use_gpu=os.getenv("STT_USE_GPU", "true").lower() == "true",
            device=os.getenv("STT_DEVICE", "cuda"),
            beam_size=int(os.getenv("STT_BEAM_SIZE", 5)),
        )
        
        self.tts = TTSConfig(
            engine=os.getenv("TTS_ENGINE", "pyttsx3"),
            rate=int(os.getenv("TTS_RATE", 150)),
            volume=float(os.getenv("TTS_VOLUME", 1.0)),
        )
        
        self.safety = SafetyConfig(
            require_confirmation_threshold=float(
                os.getenv("SAFETY_CONFIRMATION_THRESHOLD", 0.6)
            ),
            min_confidence=float(os.getenv("SAFETY_MIN_CONFIDENCE", 0.3)),
            dangerous_actions_require_confirmation=(
                os.getenv("SAFETY_REQUIRE_CONFIRMATION", "true").lower() == "true"
            ),
        )
        
        self.execution = ExecutionConfig(
            max_retries=int(os.getenv("EXECUTION_MAX_RETRIES", 3)),
            retry_delay_seconds=float(os.getenv("EXECUTION_RETRY_DELAY", 1.0)),
            timeout_seconds=float(os.getenv("EXECUTION_TIMEOUT", 30.0)),
        )
        
        self.cache = CacheConfig(
            enable_cache=os.getenv("CACHE_ENABLE", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("CACHE_TTL", 3600)),
        )
        
        self.logging = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_console_output=(
                os.getenv("LOG_CONSOLE", "true").lower() == "true"
            ),
        )
        
        self.api = APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", 8000)),
            debug=self.environment == Environment.DEVELOPMENT,
        )
        
        self.persistence = PersistenceConfig(
            db_type=os.getenv("DB_TYPE", "sqlite"),
            db_path=os.getenv("DB_PATH", "data/assistant.db"),
        )
        
        self._validate()

    def _validate(self):
        """Validate configuration values"""
        if self.audio.sample_rate < 8000:
            raise ValueError("Sample rate must be at least 8000 Hz")
        
        if self.audio.frame_duration_ms not in [10, 20, 30]:
            raise ValueError("Frame duration must be 10, 20, or 30 ms")
        
        if self.safety.min_confidence < 0 or self.safety.min_confidence > 1.0:
            raise ValueError("Min confidence must be between 0 and 1")
        
        if self.api.port < 1024 or self.api.port > 65535:
            raise ValueError("API port must be between 1024 and 65535")

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "environment": self.environment.value,
            "audio": asdict(self.audio),
            "stt": asdict(self.stt),
            "tts": asdict(self.tts),
            "safety": asdict(self.safety),
            "execution": asdict(self.execution),
            "cache": asdict(self.cache),
            "logging": asdict(self.logging),
            "api": asdict(self.api),
            "persistence": asdict(self.persistence),
        }

    def to_json(self, filepath: str = "config.json"):
        """Export configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_env(cls) -> "ConfigManager":
        """Load configuration from environment"""
        return cls()


# Global config instance
_config_instance: Optional[ConfigManager] = None


def init_config(env: Optional[str] = None) -> ConfigManager:
    """Initialize global configuration"""
    global _config_instance
    _config_instance = ConfigManager(env)
    return _config_instance


def get_config() -> ConfigManager:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
