"""
MMAI Infrastructure Package
Production-grade utilities for logging, configuration, error handling, caching, persistence, and monitoring

Modules:
  - logger: Structured logging with JSON output
  - config_manager: Environment-based configuration management
  - error_handling: Retry logic, circuit breaker, error recovery
  - cache: Multiple cache backends with TTL support
  - persistence: SQLite-based persistence for history and state
  - health_monitor: Real-time system health monitoring
  - validation: Input validation and sanitization
"""

from infrastructure.logger import (
    get_logger,
    init_logger,
    StructuredLogger,
    LogLevel
)

from infrastructure.config_manager import (
    get_config,
    init_config,
    ConfigManager,
    Environment
)

from infrastructure.error_handling import (
    get_error_handler,
    init_error_handler,
    retry_with_backoff,
    CircuitBreaker,
    CircuitBreakerException,
    RetryConfig
)

from infrastructure.cache import (
    get_cache,
    init_cache,
    CacheManager,
    InMemoryCache,
    FileCache
)

from infrastructure.persistence import (
    get_persistence,
    init_persistence,
    PersistenceLayer,
    ActionRecord,
    SessionRecord
)

from infrastructure.health_monitor import (
    get_health_monitor,
    init_health_monitor,
    HealthMonitor,
    HealthStatus,
    MetricsCollector
)

from infrastructure.validation import (
    InputValidator,
    ValidationError,
    RateLimiter,
    SanitizeString
)

__all__ = [
    # Logger
    "get_logger",
    "init_logger",
    "StructuredLogger",
    "LogLevel",
    # Config
    "get_config",
    "init_config",
    "ConfigManager",
    "Environment",
    # Error Handling
    "get_error_handler",
    "init_error_handler",
    "retry_with_backoff",
    "CircuitBreaker",
    "CircuitBreakerException",
    "RetryConfig",
    # Cache
    "get_cache",
    "init_cache",
    "CacheManager",
    "InMemoryCache",
    "FileCache",
    # Persistence
    "get_persistence",
    "init_persistence",
    "PersistenceLayer",
    "ActionRecord",
    "SessionRecord",
    # Health Monitor
    "get_health_monitor",
    "init_health_monitor",
    "HealthMonitor",
    "HealthStatus",
    "MetricsCollector",
    # Validation
    "InputValidator",
    "ValidationError",
    "RateLimiter",
    "SanitizeString",
]
