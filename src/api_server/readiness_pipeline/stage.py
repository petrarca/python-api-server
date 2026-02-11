"""Readiness pipeline stage implementation for grouped checks.

This module provides the ReadinessStage class, which represents a logical grouping
of related readiness checks. Stages provide a way to organize checks into
meaningful units (e.g., database validation, service initialization) and
manage their execution with configurable behavior like fail-fast and critical
failure handling.

Key Features:
- Logical grouping of related readiness checks
- Configurable execution behavior (fail_fast, critical, run_once)
- Stage-level result aggregation and timing
- Integration with check executor and result processor
- Fluent interface for building stages
- Support for stage skipping and early termination

Typical Usage:
    stage = ReadinessStage(
        name="database_validation",
        description="Validates database connectivity and schema",
        is_critical=True,
        fail_fast=True
    )
    .add_check(DatabaseConnectionCheck())
    .add_check(DatabaseSchemaCheck())

    result = stage.execute()
    if result.status == CheckStatus.SUCCESS:
        print("Database validation passed")
"""

import arrow
from loguru import logger

from api_server.readiness_pipeline.base import ReadinessCheck
from api_server.readiness_pipeline.check_executor import CheckExecutor
from api_server.readiness_pipeline.enums import CheckStatus
from api_server.readiness_pipeline.models import ReadinessStageResult

from .processor import ResultProcessor


class ReadinessStage:
    """A readiness pipeline stage containing logically related checks.

    ReadinessStage provides a container for grouping related readiness checks
    and managing their execution as a unit. Each stage can be configured with
    different execution behaviors and provides aggregated results for all
    contained checks.

    This class provides:
    - Check grouping and organization
    - Configurable execution behavior (critical, fail_fast, run_once)
    - Stage-level result aggregation and statistics
    - Integration with check execution and result processing components
    - Fluent interface for stage construction

    Attributes:
        name: Unique identifier for this stage
        description: Human-readable description of stage purpose
        is_critical: Whether failure stops the entire pipeline
        fail_fast: Whether to stop on first check failure
        run_once: Whether to cache and reuse results
        checks: List of ReadinessCheck objects in this stage
    """

    def __init__(
        self,
        name: str,
        description: str,
        is_critical: bool = False,
        fail_fast: bool = True,
        run_once: bool = False,
    ):
        """Initialize the readiness pipeline stage with configuration.

        Args:
            name: Name of this stage (used for identification and logging)
            description: Description of what this stage checks
            is_critical: If True, failure stops the entire pipeline
            fail_fast: If True, stop stage execution on first check failure
            run_once: If True, this stage will only run once and reuse the result
        """
        self.name = name
        self.description = description
        self.is_critical = is_critical
        self.fail_fast = fail_fast
        self.run_once = run_once
        self.checks: list[ReadinessCheck] = []
        self._executed_once = False
        self._last_result: ReadinessStageResult | None = None

        # Initialize extracted components
        self._check_executor = CheckExecutor()
        self._result_processor = ResultProcessor()

    def add_check(self, check: ReadinessCheck) -> ReadinessStage:
        """Add a check to this readiness pipeline stage (fluent interface).

        Args:
            check: The readiness check to add to this stage

        Returns:
            Self for method chaining (fluent interface)
        """
        self.checks.append(check)
        return self

    def add_checks(self, checks: list[ReadinessCheck]) -> ReadinessStage:
        """Add multiple checks to this readiness pipeline stage.

        Args:
            checks: List of readiness checks to add

        Returns:
            This stage for method chaining
        """
        self.checks.extend(checks)
        return self

    def get_check(self, check_name: str) -> ReadinessCheck | None:
        """Get a check by name from this stage.

        Args:
            check_name: Name of the check to retrieve

        Returns:
            The check if found, None otherwise
        """
        return next((check for check in self.checks if check.name == check_name), None)

    def get_check_names(self) -> list[str]:
        """Get names of all checks in this stage.

        Returns:
            List of check names
        """
        return [check.name for check in self.checks]

    def get_last_result(self) -> ReadinessStageResult | None:
        """Get the last execution result for this stage.

        Returns:
            The last stage result if available, None otherwise
        """
        return self._last_result

    def get_status(self) -> CheckStatus | None:
        """Get the current status of this stage.

        Returns:
            The stage status if available, None otherwise
        """
        return self._last_result.status if self._last_result else None

    def is_successful(self) -> bool:
        """Check if this stage completed successfully.

        Returns:
            True if stage was successful, False otherwise
        """
        return self._last_result is not None and self._last_result.status == CheckStatus.SUCCESS

    def execute(self, force_rerun: bool = False) -> ReadinessStageResult:
        """Execute all checks in this readiness pipeline stage sequentially.

        Args:
            force_rerun: If True, ignore run_once cache and execute again

        Returns:
            ReadinessStageResult: Result of executing this stage
        """
        if not force_rerun and self.run_once and self._executed_once and self._last_result is not None:
            logger.debug(f"Skipping stage '{self.name}' - already executed (run_once=True)")
            return self._last_result

        result = self._execute_stage(force_rerun)

        if self.run_once:
            self._executed_once = True
            self._last_result = result

        return result

    def rerun(self) -> ReadinessStageResult:
        """Force re-execution of the stage, ignoring run_once cache.

        This is a convenience method equivalent to execute(force_rerun=True).

        Returns:
            ReadinessStageResult: Result of executing this stage
        """
        return self.execute(force_rerun=True)

    def _execute_stage(self, force_rerun: bool = False) -> ReadinessStageResult:
        """Execute the stage logic without run_once handling.

        Args:
            force_rerun: If True, pass to checks to ignore their run_once cache
        """
        logger.info(f"Executing pipeline stage: {self.name}")
        start_time = arrow.utcnow().float_timestamp
        executed_at = arrow.utcnow().isoformat()

        result = ReadinessStageResult(
            stage_name=self.name,
            status=CheckStatus.RUNNING,
            message=f"Executing {self.name} stage",
            executed_at=executed_at,
            total_checks=len(self.checks),
            run_once=self.run_once,
        )

        for check in self.checks:
            should_stop = self._execute_single_check(check, result, force_rerun)
            if should_stop:
                break

        # Set final stage status if still running
        self._result_processor.finalize_stage_result(result, self.name)

        result.execution_time_ms = (arrow.utcnow().float_timestamp - start_time) * 1000
        logger.info(f"Stage {self.name} completed with status {result.status.value} in {result.execution_time_ms:.1f}ms")
        return result

    def _execute_single_check(self, check: ReadinessCheck, result: ReadinessStageResult, force_rerun: bool = False) -> bool:
        """Execute a single check and update the result.

        Args:
            check: The check to execute
            result: The stage result to update
            force_rerun: If True, pass to check to ignore run_once cache

        Returns:
            bool: True if stage execution should stop, False to continue
        """
        # Use check executor to run the check
        check_result = self._check_executor.execute_single_check(check, self.name, force_rerun)
        result.check_results.append(check_result)

        # Use result processor to handle the check result
        should_stop, stop_reason = self._result_processor.process_check_result(check, check_result, self.name, self.fail_fast)

        # Update counters based on check result
        if check_result.status == CheckStatus.SUCCESS:
            result.successful_checks += 1
        elif check_result.status == CheckStatus.NOT_APPLICABLE or check_result.status == CheckStatus.SKIP_STAGE:
            result.skipped_checks += 1
        else:
            result.failed_checks += 1

        if should_stop and stop_reason:
            result.status = CheckStatus.SKIPPED if "skipped" in stop_reason.lower() else CheckStatus.FAILED
            result.message = stop_reason

            # Mark remaining checks as skipped if needed
            if result.status == CheckStatus.SKIPPED:
                self._result_processor.mark_remaining_checks_skipped(result, check, self.checks, self.name, "due to stage skip")
            elif result.status == CheckStatus.FAILED:
                self._result_processor.mark_remaining_checks_skipped(result, check, self.checks, self.name, "due to fail-fast")

        return should_stop

    def reset(self) -> None:
        """Reset the execution state to initial conditions."""
        self._executed_once = False
        self._last_result = None
        # Reset all checks in this stage as well
        for check in self.checks:
            check.reset()

    def __str__(self) -> str:
        """String representation of the stage."""
        return f"CheckStage(name='{self.name}', checks={len(self.checks)})"

    def __repr__(self) -> str:
        """Detailed representation of the stage."""
        return (
            f"CheckStage(name='{self.name}', "
            f"description='{self.description}', "
            f"is_critical={self.is_critical}, fail_fast={self.fail_fast}, "
            f"checks={len(self.checks)})"
        )
