"""Base models and abstractions for readiness pipeline system."""

from abc import ABC, abstractmethod
from typing import Any

# Import models from separate module to avoid circular dependencies
from .enums import CheckStatus
from .models import ReadinessCheckResult


class ReadinessCheck(ABC):
    """Abstract base class for individual readiness checks."""

    def __init__(self, name: str, is_critical: bool = False, run_once: bool = False):
        """Initialize the readiness check.

        Args:
            name: The name of this readiness check (used in result.check_name field)
            is_critical: If True, failure stops the current pipeline stage
            run_once: If True, this check will only run once and reuse the
                result
        """
        self.name = name
        self.is_critical = is_critical
        self.run_once = run_once
        self._executed_once = False
        self._last_result: ReadinessCheckResult | None = None

    @abstractmethod
    def _execute(self) -> ReadinessCheckResult:
        """Execute the readiness check and return the result.

        This method should be implemented by subclasses.

        Returns:
            ReadinessCheckResult: The result of the readiness check
        """

    def run(self, force_rerun: bool = False) -> ReadinessCheckResult:
        """Execute the readiness check with run_once logic.

        Args:
            force_rerun: If True, ignore run_once cache and execute again

        Returns:
            ReadinessCheckResult: The result of the readiness check
        """
        if not force_rerun and self.run_once and self._executed_once and self._last_result is not None:
            from loguru import logger

            logger.debug(f"Skipping check '{self.name}' - already executed (run_once=True)")
            return self._last_result

        result = self._execute()

        if self.run_once:
            self._executed_once = True
            self._last_result = result

        return result

    def rerun(self) -> ReadinessCheckResult:
        """Force re-execution of the check, ignoring run_once cache.

        This is a convenience method equivalent to run(force_rerun=True).

        Returns:
            ReadinessCheckResult: The result of the readiness check
        """
        return self.run(force_rerun=True)

    def reset(self) -> None:
        """Reset the execution state to initial conditions."""
        self._executed_once = False
        self._last_result = None

    def success(self, message: str, details: dict[str, Any] | None = None) -> ReadinessCheckResult:
        """Return a successful check result."""
        return ReadinessCheckResult(
            check_name=self.name,
            status=CheckStatus.SUCCESS,
            message=message,
            details=details or {},
            run_once=self.run_once,
        )

    def failed(self, message: str, details: dict[str, Any] | None = None) -> ReadinessCheckResult:
        """Return a failed check result."""
        return ReadinessCheckResult(
            check_name=self.name,
            status=CheckStatus.FAILED,
            message=message,
            details=details or {},
            run_once=self.run_once,
        )

    def warning(self, message: str, details: dict[str, Any] | None = None) -> ReadinessCheckResult:
        """Return a warning check result."""
        return ReadinessCheckResult(
            check_name=self.name,
            status=CheckStatus.WARNING,
            message=message,
            details=details or {},
            run_once=self.run_once,
        )

    def not_applicable(self, message: str, details: dict[str, Any] | None = None) -> ReadinessCheckResult:
        """Return a not applicable check result.

        Use when a check should not run due to configuration or missing
        setup, but this is expected behavior. E.g., optional features that
        are not configured.
        """
        return ReadinessCheckResult(
            check_name=self.name,
            status=CheckStatus.NOT_APPLICABLE,
            message=message,
            details=details or {},
            run_once=self.run_once,
        )

    def skip_stage(self, message: str, details: dict[str, Any] | None = None) -> ReadinessCheckResult:
        """Return a skip stage result.

        Use to indicate that the entire stage should be skipped
        (e.g., a prerequisite check fails, making remaining checks
        meaningless).

        This will prevent execution of any remaining checks in the stage,
        but processing of the next stage will continue.
        """
        return ReadinessCheckResult(
            check_name=self.name,
            status=CheckStatus.SKIP_STAGE,
            message=message,
            details=details or {},
            run_once=self.run_once,
        )
