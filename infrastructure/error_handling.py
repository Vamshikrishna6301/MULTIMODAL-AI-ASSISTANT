"""
Production-Grade Error Handling & Recovery
Implements retry logic, circuit breaker pattern, and graceful degradation
"""

import time
from enum import Enum
from typing import Callable, TypeVar, Any, Optional
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from infrastructure.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker state machine"""
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Failures threshold exceeded
    HALF_OPEN = "half_open"     # Testing after recovery


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation
    Prevents cascading failures by failing fast when service is down
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_attempt_time: Optional[datetime] = None

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        
        # Check if we should attempt recovery
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(
                    f"Circuit breaker '{self.name}' entering HALF_OPEN state",
                    circuit_breaker=self.name
                )
            else:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            logger.info(
                f"Circuit breaker '{self.name}' reset to CLOSED",
                circuit_breaker=self.name
            )

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures",
                circuit_breaker=self.name,
                threshold=self.failure_threshold
            )

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to retry"""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retry logic with exponential backoff
    
    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def risky_operation():
            ...
    """
    cfg = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 1
            delay = cfg.initial_delay
            
            while attempt <= cfg.max_attempts:
                try:
                    logger.debug(
                        f"Attempt {attempt}/{cfg.max_attempts} for {func.__name__}"
                    )
                    return func(*args, **kwargs)
                
                except cfg.retryable_exceptions as e:
                    if attempt == cfg.max_attempts:
                        logger.error(
                            f"All retry attempts exhausted for {func.__name__}",
                            function=func.__name__,
                            attempts=attempt,
                            exception=str(e)
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt} failed, retrying in {delay}s",
                        function=func.__name__,
                        attempt=attempt,
                        delay=delay,
                        exception=str(e)
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * cfg.exponential_base, cfg.max_delay)
                    attempt += 1
        
        return wrapper
    return decorator


class ErrorHandler:
    """
    Centralized error handling with fallbacks
    """

    def __init__(self):
        self.fallback_handlers: dict = {}
        self.circuit_breakers: dict = {}

    def register_fallback(self, error_type: type, handler: Callable[[Exception], Any]):
        """Register fallback handler for specific error type"""
        self.fallback_handlers[error_type] = handler

    def register_circuit_breaker(self, name: str, breaker: CircuitBreaker):
        """Register circuit breaker for a service"""
        self.circuit_breakers[name] = breaker

    def handle_error(
        self,
        error: Exception,
        fallback_value: Optional[Any] = None,
        log_context: Optional[dict] = None
    ) -> Any:
        """
        Handle error with registered fallback
        
        Returns fallback value if handler exists, else raises
        """
        error_type = type(error)
        
        logger.error(
            f"Error handled: {error_type.__name__}",
            error_type=error_type.__name__,
            error_message=str(error),
            **(log_context or {})
        )
        
        # Check specific error handler
        if error_type in self.fallback_handlers:
            handler = self.fallback_handlers[error_type]
            try:
                return handler(error)
            except Exception as handler_error:
                logger.error(
                    "Fallback handler failed",
                    handler_error=str(handler_error)
                )
        
        # Return fallback value if available
        if fallback_value is not None:
            logger.info("Using fallback value")
            return fallback_value
        
        raise

    def protected_call(
        self,
        func: Callable[..., T],
        fallback_value: Optional[T] = None,
        **call_kwargs
    ) -> T:
        """
        Execute function with error protection
        """
        try:
            return func(**call_kwargs)
        except Exception as e:
            return self.handle_error(e, fallback_value)


# Global error handler
_error_handler: Optional[ErrorHandler] = None


def init_error_handler() -> ErrorHandler:
    """Initialize global error handler"""
    global _error_handler
    _error_handler = ErrorHandler()
    return _error_handler


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
