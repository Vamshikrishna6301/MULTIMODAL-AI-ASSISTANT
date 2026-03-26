"""
Production-Grade Input Validation & Sanitization
Prevents injection attacks and ensures data integrity
"""

import re
from typing import Any, Optional, List, Dict
from enum import Enum


class ValidationError(Exception):
    """Input validation error"""
    pass


class SanitizationType(Enum):
    """Type of sanitization to apply"""
    STRING = "string"
    COMMAND = "command"
    PATH = "path"
    JSON = "json"
    UUID = "uuid"


class InputValidator:
    """
    Comprehensive input validation and sanitization
    - Prevents command injection
    - Validates file paths
    - Sanitizes strings
    - Validates data types
    """

    # Patterns for validation
    PATTERNS = {
        "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "url": r"^https?://[^\s/$.?#].[^\s]*$",
        "safe_filename": r"^[a-zA-Z0-9._\-]+$",
        "alphanumeric": r"^[a-zA-Z0-9]*$",
    }

    # Dangerous patterns for command injection
    DANGEROUS_PATTERNS = [
        r"[;&|`$()\\]",  # Shell metacharacters
        r"<|>",  # Redirection
        r"\n|\r",  # Newlines
    ]

    # Dangerous path patterns
    DANGEROUS_PATHS = [
        r"\.\.[\\/]",  # Directory traversal
        r"^[/\\]{2,}",  # UNC paths
        r"[*?<>|]",  # Wildcard characters
    ]

    @staticmethod
    def validate_string(
        value: str,
        min_length: int = 0,
        max_length: int = 10000,
        allow_special_chars: bool = False
    ) -> str:
        """
        Validate and sanitize string input
        
        Args:
            value: String to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            allow_special_chars: Whether to allow special characters
        
        Returns:
            Sanitized string
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value)}")
        
        if len(value) < min_length:
            raise ValidationError(
                f"String too short. Minimum {min_length} characters"
            )

        if len(value) > max_length:
            raise ValidationError(
                f"String too long. Maximum {max_length} characters"
            )
        
        if not allow_special_chars:
            # Remove potentially harmful characters
            value = re.sub(r'[<>"\']', '', value)
        
        return value.strip()

    @staticmethod
    def validate_command(value: str) -> str:
        """
        Validate command string to prevent injection attacks
        
        Args:
            value: Command string to validate
        
        Returns:
            Validated command string
        
        Raises:
            ValidationError: If dangerous patterns detected
        """
        if not isinstance(value, str):
            raise ValidationError("Command must be a string")
        
        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, value):
                raise ValidationError(
                    f"Dangerous pattern detected in command: {pattern}"
                )
        
        # Limit length
        if len(value) > 1000:
            raise ValidationError("Command too long")
        
        return value.strip()

    @staticmethod
    def validate_path(value: str, must_exist: bool = False) -> str:
        """
        Validate file path to prevent directory traversal
        
        Args:
            value: Path to validate
            must_exist: Whether path must exist on filesystem
        
        Returns:
            Validated path
        
        Raises:
            ValidationError: If path is invalid or dangerous
        """
        if not isinstance(value, str):
            raise ValidationError("Path must be a string")
        
        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATHS:
            if re.search(pattern, value):
                raise ValidationError(
                    f"Dangerous path pattern detected: {pattern}"
                )
        
        # Normalize path
        import os
        normalized = os.path.normpath(value)
        
        # Prevent absolute paths to system directories
        system_dirs = ["/etc", "/sys", "/proc", "C:\\Windows", "C:\\System32"]
        if any(normalized.startswith(sd) for sd in system_dirs):
            raise ValidationError("Access to system directories not allowed")
        
        return normalized

    @staticmethod
    def validate_email(value: str) -> str:
        """Validate email address"""
        if not isinstance(value, str):
            raise ValidationError("Email must be a string")
        
        if not re.match(InputValidator.PATTERNS["email"], value):
            raise ValidationError("Invalid email format")
        
        if len(value) > 254:
            raise ValidationError("Email too long")
        
        return value.lower()

    @staticmethod
    def validate_url(value: str) -> str:
        """Validate URL"""
        if not isinstance(value, str):
            raise ValidationError("URL must be a string")
        
        if not re.match(InputValidator.PATTERNS["url"], value):
            raise ValidationError("Invalid URL format")
        
        if len(value) > 2048:
            raise ValidationError("URL too long")
        
        return value

    @staticmethod
    def validate_integer(
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """Validate integer input"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Expected integer, got {type(value)}")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(f"Value below minimum: {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"Value exceeds maximum: {max_value}")
        
        return int_value

    @staticmethod
    def validate_float(
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """Validate float input"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Expected float, got {type(value)}")
        
        if min_value is not None and float_value < min_value:
            raise ValidationError(f"Value below minimum: {min_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValidationError(f"Value exceeds maximum: {max_value}")
        
        return float_value

    @staticmethod
    def validate_choice(value: Any, choices: List[Any]) -> Any:
        """Validate that value is one of allowed choices"""
        if value not in choices:
            raise ValidationError(
                f"Value '{value}' not in allowed choices: {choices}"
            )
        return value

    @staticmethod
    def validate_dict(
        value: Any,
        required_keys: Optional[List[str]] = None,
        allowed_keys: Optional[List[str]] = None
    ) -> Dict:
        """Validate dictionary structure"""
        if not isinstance(value, dict):
            raise ValidationError(f"Expected dict, got {type(value)}")
        
        if required_keys:
            missing = set(required_keys) - set(value.keys())
            if missing:
                raise ValidationError(f"Missing required keys: {missing}")
        
        if allowed_keys:
            invalid = set(value.keys()) - set(allowed_keys)
            if invalid:
                raise ValidationError(f"Invalid keys: {invalid}")
        
        return value


class SanitizeString:
    """String sanitization utilities"""

    @staticmethod
    def remove_null_bytes(value: str) -> str:
        """Remove null bytes from string"""
        return value.replace('\x00', '')

    @staticmethod
    def remove_control_chars(value: str) -> str:
        """Remove control characters"""
        return ''.join(c for c in value if ord(c) >= 32 or c in '\n\r\t')

    @staticmethod
    def escape_html(value: str) -> str:
        """Escape HTML special characters"""
        return (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    @staticmethod
    def escape_shell(value: str) -> str:
        """Escape shell special characters"""
        # Quote the entire string
        return f"'{value.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"


class RateLimiter:
    """Simple rate limiting implementation"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for user"""
        import time
        
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if t > cutoff_time
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(current_time)
        return True
