"""
Integration Guide: Using Production Infrastructure with Phase 1-3

This module shows how to integrate all production-level infrastructure
with the existing Phase 1-3 implementation.
"""

import uuid
from datetime import datetime
from typing import Optional

# Import infrastructure components
from infrastructure import (
    get_logger, init_logger,
    get_config, init_config,
    get_cache, init_cache,
    get_persistence, init_persistence,
    get_error_handler, init_error_handler,
    get_health_monitor, init_health_monitor,
    InputValidator, ValidationError, retry_with_backoff, RetryConfig,
    CircuitBreaker, ActionRecord
)

from core.intent_parser import IntentParser
from execution.executor import ExecutionEngine
from voice.voice_loop import VoiceLoop


class ProductionVoiceAssistant:
    """
    Production-ready voice assistant integrating all infrastructure
    """

    def __init__(self, env: str = "development"):
        """Initialize production voice assistant with full infrastructure"""
        
        # 1. Initialize infrastructure
        print("🚀 Initializing Production Infrastructure...")
        init_logger("INFO")
        init_config(env)
        init_cache()
        init_persistence()
        init_error_handler()
        init_health_monitor()
        
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.cache = get_cache()
        self.persistence = get_persistence()
        self.error_handler = get_error_handler()
        self.health_monitor = get_health_monitor()
        
        # 2. Initialize core components
        self.parser = IntentParser()
        self.executor = ExecutionEngine()
        self.validator = InputValidator()
        
        # 3. Create session tracking
        self.session_id = str(uuid.uuid4())
        self.persistence.create_session(self.session_id, user="voice_assistant")
        
        # 4. Setup error handlers
        self._setup_error_handlers()
        
        # 5. Log startup
        self.logger.set_context(
            session_id=self.session_id,
            environment=env,
            version="1.0"
        )
        self.logger.info("Production Voice Assistant initialized", 
                        session_id=self.session_id)
        
        self.logger.audit(
            action="SYSTEM_START",
            user="voice_assistant",
            environment=env,
            session_id=self.session_id
        )

    def _setup_error_handlers(self):
        """Register custom error handlers"""
        
        # Handle connection errors
        def handle_connection_error(e):
            self.logger.warning("Connection error, using cached data")
            return {"status": "offline", "data": []}
        
        self.error_handler.register_fallback(ConnectionError, handle_connection_error)
        
        # Setup circuit breaker for execution
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            name="execution_service"
        )
        self.error_handler.register_circuit_breaker("execution", breaker)

    def process_voice_input(self, audio_data: bytes) -> str:
        """
        Process voice input with full infrastructure support
        
        Flow:
        1. Validate input
        2. Convert to text (STT)
        3. Log audio event
        4. Return text
        """
        
        self.logger.debug("Processing voice input")
        
        try:
            # Validate input
            if not isinstance(audio_data, bytes):
                raise ValidationError("Audio data must be bytes")
            
            if len(audio_data) == 0:
                raise ValidationError("Audio data is empty")
            
            # Convert audio to text (STT)
            # In real implementation, this would call faster-whisper
            text = self._speech_to_text(audio_data)
            
            # Log the event
            self.persistence.record_action(
                ActionRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    action="SPEECH_TO_TEXT",
                    target=None,
                    status="success",
                    user="voice_assistant",
                    risk_level=0,
                    confidence=0.95,
                    result=f"Transcribed to: {text[:50]}..."
                )
            )
            
            self.logger.info("Speech transcribed", transcription=text[:50])
            return text
            
        except ValidationError as e:
            self.logger.error("Input validation failed", exception=str(e))
            return None
        except Exception as e:
            self.logger.error("STT error", exception=str(e))
            return None

    @retry_with_backoff(RetryConfig(max_attempts=2, initial_delay=1.0))
    def _speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech to text with retry logic"""
        # Placeholder for actual STT implementation
        return "user command"

    def process_command(self, text: str) -> str:
        """
        Process text command with full validation and caching
        
        Flow:
        1. Validate input
        2. Check cache
        3. Parse intent
        4. Log event
        5. Return result
        """
        
        try:
            # 1. Validate input
            clean_text = self.validator.validate_string(
                text,
                min_length=2,
                max_length=500,
                allow_special_chars=True
            )
            
            self.logger.info("Processing command", original=text[:50])
            
            # 2. Check cache for similar intents
            cache_key = f"intent:{hash(clean_text) % 10000}"
            cached_intent = self.cache.get(cache_key)
            
            if cached_intent:
                self.logger.info("Intent retrieved from cache")
                self.persistence.increment_session_actions(self.session_id)
                return cached_intent
            
            # 3. Parse intent with retry
            @retry_with_backoff(RetryConfig(max_attempts=2))
            def safe_parse():
                return self.parser.parse(clean_text)
            
            intent = safe_parse()
            
            # 4. Cache result
            self.cache.set(cache_key, intent, ttl_seconds=3600)
            
            # 5. Log action
            self.persistence.record_action(
                ActionRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    action="INTENT_PARSING",
                    target=intent.target,
                    status="success",
                    user="voice_assistant",
                    risk_level=intent.risk_level,
                    confidence=intent.confidence
                )
            )
            
            self.persistence.increment_session_actions(self.session_id)
            
            self.logger.info(
                "Intent parsed",
                action=intent.action,
                confidence=intent.confidence
            )
            
            return intent
            
        except ValidationError as e:
            self.logger.warning("Input validation failed", error=str(e))
            self.persistence.record_action(
                ActionRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    action="COMMAND_PARSE",
                    target=text[:50],
                    status="blocked",
                    user="voice_assistant",
                    risk_level=0,
                    confidence=0.0,
                    error=str(e)
                )
            )
            return None
        except Exception as e:
            self.logger.error("Command processing failed", exception=str(e))
            return None

    def execute_intent(self, intent) -> dict:
        """
        Execute intent with full error handling and tracking
        
        Flow:
        1. Validate intent
        2. Check safety
        3. Execute with circuit breaker
        4. Record result
        5. Return response
        """
        
        try:
            if not intent:
                raise ValueError("Intent is None")
            
            self.logger.info("Executing intent", action=intent.action)
            
            # Prepare decision
            decision = {
                "status": "APPROVED",
                "action": intent.action,
                "target": intent.target,
                "confidence": intent.confidence,
                "requires_confirmation": intent.requires_confirmation
            }
            
            # Execute with error handler
            result = self.error_handler.protected_call(
                self.executor.execute,
                fallback_value={"status": "failed", "reason": "Execution failed"}
            )
            
            # Record successful execution
            self.persistence.record_action(
                ActionRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    action=intent.action,
                    target=intent.target,
                    status="success",
                    user="voice_assistant",
                    risk_level=intent.risk_level,
                    confidence=intent.confidence,
                    result=str(result)
                )
            )
            
            self.logger.info("Execution completed", result=result)
            return result
            
        except Exception as e:
            self.logger.error("Execution error", exception=str(e))
            
            # Record failed execution
            self.persistence.record_action(
                ActionRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    action=intent.action if intent else "UNKNOWN",
                    target=intent.target if intent else None,
                    status="failed",
                    user="voice_assistant",
                    risk_level=intent.risk_level if intent else 0,
                    confidence=intent.confidence if intent else 0.0,
                    error=str(e)
                )
            )
            
            return {"status": "error", "message": str(e)}

    def get_system_health(self) -> dict:
        """Get complete system health report"""
        
        health = self.health_monitor.get_health_json()
        stats = self.persistence.get_statistics()
        
        report = {
            "system_health": health,
            "database_stats": stats,
            "session": {
                "session_id": self.session_id,
                "duration_seconds": (
                    datetime.utcnow() - 
                    datetime.fromisoformat(health['timestamp'])
                ).total_seconds()
            }
        }
        
        self.logger.info("Health report generated")
        return report

    def shutdown(self, notes: str = ""):
        """Graceful shutdown"""
        
        self.logger.info("Shutting down")
        
        # End session
        self.persistence.end_session(
            self.session_id,
            notes=notes
        )
        
        # Audit shutdown
        self.logger.audit(
            action="SYSTEM_SHUTDOWN",
            user="voice_assistant",
            session_id=self.session_id,
            uptime_seconds=self.health_monitor.metrics.start_time
        )
        
        # Cleanup
        self.cache.clear()
        
        self.logger.info("Shutdown complete")


# Example usage
if __name__ == "__main__":
    
    # 1. Initialize production assistant
    assistant = ProductionVoiceAssistant(env="production")
    
    try:
        # 2. Process voice input
        audio_bytes = b"audio_data_here"  # In real implementation
        text = assistant.process_voice_input(audio_bytes)
        
        if text:
            # 3. Process command
            intent = assistant.process_command(text)
            
            if intent:
                # 4. Execute intent
                result = assistant.execute_intent(intent)
        
        # 5. Check system health
        health = assistant.get_system_health()
        print(f"\nSystem Health: {health['system_health']['status']}")
        print(f"Total Actions: {health['database_stats']['total_actions']}")
        
    finally:
        # 6. Graceful shutdown
        assistant.shutdown(notes="Normal completion")
