from dataclasses import dataclass
from typing import Optional, Dict, Any
import time


@dataclass
class UnifiedResponse:
    success: bool
    category: str  # execution | utility | knowledge
    spoken_message: str
    technical_message: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def success_response(
        category: str,
        spoken_message: str,
        technical_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        return UnifiedResponse(
            success=True,
            category=category,
            spoken_message=spoken_message,
            technical_message=technical_message,
            execution_time_ms=round(time.time() * 1000, 2),
            metadata=metadata or {},
        )

    @staticmethod
    def error_response(
        category: str,
        spoken_message: str,
        error_code: str,
        technical_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        return UnifiedResponse(
            success=False,
            category=category,
            spoken_message=spoken_message,
            technical_message=technical_message,
            error_code=error_code,
            execution_time_ms=round(time.time() * 1000, 2),
            metadata=metadata or {},
        )
