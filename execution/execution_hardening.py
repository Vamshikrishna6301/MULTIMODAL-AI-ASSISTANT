from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.response_model import UnifiedResponse
from infrastructure.error_handling import CircuitBreaker, CircuitBreakerException


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    base_delay_seconds: float = 0.15
    retryable_error_codes: set = field(default_factory=set)
    retry_on_exception: bool = True
    enable_rollback: bool = False


@dataclass
class ExecutionAttempt:
    attempt: int
    success: bool
    error_code: Optional[str]
    technical_message: Optional[str]
    duration_ms: float


@dataclass
class ExecutionRecoveryResult:
    response: UnifiedResponse
    attempts: List[ExecutionAttempt]
    rollback_attempted: bool = False
    rollback_succeeded: bool = False
    circuit_opened: bool = False


class ExecutionHardeningManager:
    """
    Adds retry, rollback, and circuit breaker behavior around adapter execution.
    """

    def __init__(self):
        self.policies = self._default_policies()
        self.circuit_breakers = {
            action: CircuitBreaker(
                failure_threshold=3 if action in {"VISION", "CLICK_INDEX", "CLICK_NAME"} else 5,
                recovery_timeout=10.0,
                name=f"execution:{action.lower()}",
            )
            for action in self.policies
        }

    def execute(
        self,
        action: str,
        operation: Callable[[], UnifiedResponse],
        rollback: Optional[Callable[[], bool]] = None,
    ) -> ExecutionRecoveryResult:
        policy = self.policies.get(action, RetryPolicy())
        attempts: List[ExecutionAttempt] = []
        rollback_attempted = False
        rollback_succeeded = False
        circuit_opened = False
        last_response: Optional[UnifiedResponse] = None

        breaker = self.circuit_breakers.get(action)

        for attempt_number in range(1, policy.max_attempts + 1):
            started = time.perf_counter()

            try:
                response = breaker.call(operation) if breaker else operation()
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                attempts.append(
                    ExecutionAttempt(
                        attempt=attempt_number,
                        success=response.success,
                        error_code=response.error_code,
                        technical_message=response.technical_message,
                        duration_ms=elapsed_ms,
                    )
                )
                last_response = response

                if response.success:
                    return ExecutionRecoveryResult(
                        response=self._attach_metadata(response, attempts, rollback_attempted, rollback_succeeded),
                        attempts=attempts,
                        rollback_attempted=rollback_attempted,
                        rollback_succeeded=rollback_succeeded,
                        circuit_opened=circuit_opened,
                    )

                if not self._should_retry_response(response, policy, attempt_number):
                    break

            except CircuitBreakerException as exc:
                circuit_opened = True
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                attempts.append(
                    ExecutionAttempt(
                        attempt=attempt_number,
                        success=False,
                        error_code="CIRCUIT_OPEN",
                        technical_message=str(exc),
                        duration_ms=elapsed_ms,
                    )
                )
                last_response = UnifiedResponse.error_response(
                    category="execution",
                    spoken_message="This action is temporarily unavailable after repeated failures.",
                    error_code="CIRCUIT_OPEN",
                    technical_message=str(exc),
                )
                break

            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                attempts.append(
                    ExecutionAttempt(
                        attempt=attempt_number,
                        success=False,
                        error_code="EXECUTION_EXCEPTION",
                        technical_message=str(exc),
                        duration_ms=elapsed_ms,
                    )
                )
                last_response = UnifiedResponse.error_response(
                    category="execution",
                    spoken_message="Execution failed due to an internal adapter error.",
                    error_code="EXECUTION_EXCEPTION",
                    technical_message=str(exc),
                )
                if not (policy.retry_on_exception and attempt_number < policy.max_attempts):
                    break

            if attempt_number < policy.max_attempts:
                time.sleep(policy.base_delay_seconds * attempt_number)

        if policy.enable_rollback and rollback and last_response and not last_response.success:
            rollback_attempted = True
            try:
                rollback_succeeded = bool(rollback())
            except Exception:
                rollback_succeeded = False

        if last_response is None:
            last_response = UnifiedResponse.error_response(
                category="execution",
                spoken_message="Execution failed before a response was produced.",
                error_code="NO_RESPONSE",
            )

        return ExecutionRecoveryResult(
            response=self._attach_metadata(last_response, attempts, rollback_attempted, rollback_succeeded),
            attempts=attempts,
            rollback_attempted=rollback_attempted,
            rollback_succeeded=rollback_succeeded,
            circuit_opened=circuit_opened,
        )

    def _attach_metadata(
        self,
        response: UnifiedResponse,
        attempts: List[ExecutionAttempt],
        rollback_attempted: bool,
        rollback_succeeded: bool,
    ) -> UnifiedResponse:
        metadata = dict(response.metadata or {})
        metadata["attempt_count"] = len(attempts)
        metadata["attempts"] = [
            {
                "attempt": item.attempt,
                "success": item.success,
                "error_code": item.error_code,
                "duration_ms": item.duration_ms,
            }
            for item in attempts
        ]
        metadata["rollback_attempted"] = rollback_attempted
        metadata["rollback_succeeded"] = rollback_succeeded
        response.metadata = metadata
        return response

    def _should_retry_response(
        self,
        response: UnifiedResponse,
        policy: RetryPolicy,
        attempt_number: int,
    ) -> bool:
        return (
            not response.success
            and attempt_number < policy.max_attempts
            and (
                response.error_code in policy.retryable_error_codes
                or response.error_code is None
            )
        )

    def _default_policies(self) -> Dict[str, RetryPolicy]:
        return {
            "OPEN_APP": RetryPolicy(max_attempts=2, retryable_error_codes={"APP_OPEN_FAILED"}, enable_rollback=True),
            "SEARCH": RetryPolicy(max_attempts=2, retryable_error_codes={"SEARCH_FAILED", "SEARCH_ERROR"}),
            "TYPE_TEXT": RetryPolicy(max_attempts=2, retryable_error_codes={"TYPE_ERROR"}, enable_rollback=True),
            "FILE_OPERATION": RetryPolicy(max_attempts=2, retryable_error_codes={"FILE_OPERATION_FAILED"}),
            "SYSTEM_CONTROL": RetryPolicy(max_attempts=1, retryable_error_codes=set()),
            "VISION": RetryPolicy(max_attempts=2, retryable_error_codes={"VISION_ERROR"}),
            "CLICK_INDEX": RetryPolicy(max_attempts=2, retryable_error_codes={"UIA_ERROR", "CLICK_FAILED"}),
            "CLICK_NAME": RetryPolicy(max_attempts=2, retryable_error_codes={"UIA_ERROR", "CLICK_FAILED"}),
        }
