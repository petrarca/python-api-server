"""Check execution components for readiness pipeline stages.

This module provides the CheckExecutor class responsible for executing individual
readiness checks within pipeline stages. It handles timing, exception management,
and result enrichment with traceability information.

Key Features:
- Individual check execution with timing measurement
- Exception handling and conversion to failed results
- Result enrichment with stage names and execution timestamps
- Comprehensive logging for debugging and monitoring
- Additional feature for improved logging

"""

import arrow
from loguru import logger

from .base import CheckStatus, ReadinessCheck, ReadinessCheckResult


class CheckExecutor:
    """Handles individual check execution within readiness stages.

    The CheckExecutor is responsible for running individual ReadinessCheck instances,
    measuring their execution time, handling exceptions, and enriching the results
    with traceability information such as stage names and timestamps.

    This class provides a clean separation between the orchestration of check
    execution (handled by ReadinessStage) and the actual execution mechanics.
    It ensures consistent error handling and result formatting across all checks
    in the pipeline.

    Attributes:
        None (stateless executor - all state is in the results)
    """

    def execute_single_check(
        self,
        check: ReadinessCheck,
        stage_name: str,
        force_rerun: bool = False,
    ) -> ReadinessCheckResult:
        """Execute a single check and return its enriched result.

        This method executes a ReadinessCheck instance, measures execution time,
        handles any exceptions that occur during execution, and enriches the result
        with traceability information including stage name and execution timestamp.

        Args:
            check: The ReadinessCheck instance to execute. Must implement the
                  _execute() method and handle run_once logic internally.
            stage_name: Name of the stage executing this check. Used for
                       traceability and debugging purposes.
            force_rerun: If True, passes through to the check's run() method to
                        bypass any run_once caching. Useful for testing and forced
                        re-execution scenarios.

        Returns:
            ReadinessCheckResult: Enriched result containing execution status,
                timing, timestamp, stage name, and exception details if applicable.

        Raises:
            No exceptions are raised - all errors are captured and converted
            to failed results with appropriate error details.
        """
        logger.debug(f"Running check: {check.name}")
        check_start_time = arrow.utcnow().float_timestamp
        executed_at = arrow.utcnow().isoformat()

        try:
            check_result = check.run(force_rerun=force_rerun)
            check_result.executed_at = executed_at
            check_result.execution_time_ms = (arrow.utcnow().float_timestamp - check_start_time) * 1000
            # Add stage name for traceability
            check_result.stage_name = stage_name
            return check_result

        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            return self._handle_check_exception(check, e, check_start_time, stage_name)

    def _handle_check_exception(
        self,
        check: ReadinessCheck,
        e: Exception,
        check_start_time: float,
        stage_name: str,
    ) -> ReadinessCheckResult:
        """Handle unexpected exceptions during check execution.

        Converts any exception thrown during check execution into a standardized
        failed result. Ensures that even when checks fail unexpectedly, the pipeline
        can continue and provide meaningful error information for debugging.

        Args:
            check: The ReadinessCheck instance that threw the exception.
            e: The exception that was thrown during check execution.
            check_start_time: The timestamp when the check execution started,
                             used to calculate partial execution time.
            stage_name: Name of the stage that was executing the check,
                       used for traceability.

        Returns:
            ReadinessCheckResult: A failed result containing error details,
                execution time up to the point of failure, and traceability information.
        """
        executed_at = arrow.utcnow().isoformat()
        error_result = ReadinessCheckResult(
            status=CheckStatus.FAILED,
            message=f"Check execution failed: {str(e)}",
            check_name=check.name,
            stage_name=stage_name,  # Add stage name for traceability
            execution_time_ms=(arrow.utcnow().float_timestamp - check_start_time) * 1000,
            executed_at=executed_at,
            details={"exception": str(e), "type": type(e).__name__},
        )

        logger.error(f"Check {check.name} threw exception: {e}")
        return error_result
