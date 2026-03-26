"""
PRODUCTION LOGGING SYSTEM
Centralized logging with rotating file handlers and metrics
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import json

from config_production import LOGGING_CONFIG, DEBUG_MODE, ENVIRONMENT


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": ENVIRONMENT,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ProductionLogger:
    """Production-grade logging with rotation and error tracking."""
    
    def __init__(self):
        self.logger = logging.getLogger("multimodal-ai")
        self.error_logger = logging.getLogger("multimodal-ai.errors")
        self.metrics_logger = logging.getLogger("multimodal-ai.metrics")
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Configure all loggers."""
        # Main logger
        self._configure_logger(
            self.logger,
            LOGGING_CONFIG["level"],
            LOGGING_CONFIG["log_file"],
            is_error=False
        )
        
        # Error logger
        self._configure_logger(
            self.error_logger,
            "ERROR",
            LOGGING_CONFIG["error_file"],
            is_error=True
        )
        
        # Metrics logger
        metrics_file = LOGGING_CONFIG["log_file"].parent / "metrics.log"
        self._configure_logger(
            self.metrics_logger,
            "INFO",
            metrics_file,
            is_error=False
        )
    
    def _configure_logger(
        self,
        logger: logging.Logger,
        level: str,
        log_file: Path,
        is_error: bool = False
    ):
        """Configure individual logger with handlers."""
        logger.setLevel(getattr(logging, level))
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Rotating file handler
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOGGING_CONFIG["max_bytes"],
            backupCount=LOGGING_CONFIG["backup_count"]
        )
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
        
        # Console handler
        if LOGGING_CONFIG["console_output"] and not is_error:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter(LOGGING_CONFIG["format"])
            )
            logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get named logger."""
        return logging.getLogger(f"multimodal-ai.{name}")
    
    def log_info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def log_error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self.error_logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """Log debug message."""
        if DEBUG_MODE:
            self.logger.debug(message, extra=kwargs)
    
    def log_metrics(self, metrics: dict):
        """Log metrics data."""
        self.metrics_logger.info("METRICS", extra=metrics)
    
    def log_execution(self, action: str, status: str, duration_ms: float, **kwargs):
        """Log execution metrics."""
        log_data = {
            "action": action,
            "status": status,  # success, failure, timeout
            "duration_ms": duration_ms,
            **kwargs
        }
        self.log_metrics(log_data)


# Global logger instance
_logger: Optional[ProductionLogger] = None


def get_production_logger() -> ProductionLogger:
    """Get or create global logger."""
    global _logger
    if _logger is None:
        _logger = ProductionLogger()
    return _logger


def get_logger(name: str) -> logging.Logger:
    """Get named logger."""
    return get_production_logger().get_logger(name)
