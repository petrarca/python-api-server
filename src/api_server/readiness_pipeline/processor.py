"""Result processing and decision logic components for readiness stages.

This module provides the ResultProcessor class responsible for processing
check results and making execution flow decisions. It handles the logic for
determining whether stage execution should continue based on check outcomes,
including fail-fast behavior and stage skipping scenarios.

Key Features:
- Check result processing and validation
- Fail-fast decision logic for early termination
- Stage skipping based on check results
- Comprehensive logging for debugging and monitoring
- Support for different check statuses (SUCCESS/FAILED/SKIP_STAGE etc.)

Typical Usage:
    processor = ResultProcessor()
    should_stop, reason = processor.process_check_result(
        check, result, "database_stage", fail_fast=True
    )

    if should_stop:
        print(f"Stopping stage: {reason}")
"""

from loguru import logger

from api_server.readiness_pipeline.base import ReadinessCheck
from api_server.readiness_pipeline.enums import CheckStatus
from api_server.readiness_pipeline.models import ReadinessCheckResult, ReadinessStageResult


class ResultProcessor:
    """Handles result processing and decision logic for readiness stages.

    The ResultProcessor is responsible for evaluating check results and making
    decisions about stage execution flow. It implements the business logic for
    fail-fast behavior, stage skipping, and continuation decisions based on
    the outcomes of individual readiness checks.

    This class provides:
    - Check result evaluation and status processing
    - Fail-fast logic for early stage termination
    - Stage skipping decisions based on check requests
    - Detailed logging for execution tracking

    Attributes:
        None (stateless processor - pure decision logic)
    """

    def process_check_result(
        self,
        check: ReadinessCheck,
        check_result: ReadinessCheckResult,
        stage_name: str,
        fail_fast: bool = False,
    ) -> tuple[bool, str]:
        """Process a check result and determine if stage should stop.

        Evaluates the result of a check execution and decides whether the
        containing stage should continue execution or stop. Handles different
        check statuses including success, failure, not applicable, and stage
        skip requests.

        Args:
            check: The check that was executed
            check_result: The result from the check execution
            stage_name: Name of the stage for logging purposes
            fail_fast: Whether the stage should stop on first failure

        Returns:
            tuple: (should_stop: bool, stop_reason: str)
                - should_stop: True if stage execution should stop
                - stop_reason: Human-readable reason for stopping (empty if not stopping)
        """
        if check_result.status == CheckStatus.SUCCESS:
            logger.debug("Check {} passed", check.name)
            return False, ""
        elif check_result.status == CheckStatus.NOT_APPLICABLE:
            logger.info("Check {} not applicable: {}", check.name, check_result.message)
            return False, ""
        elif check_result.status == CheckStatus.SKIP_STAGE:
            logger.info("Check {} requested stage skip: {}", check.name, check_result.message)
            return True, f"Stage '{stage_name}' skipped due to check '{check.name}'"
        else:
            logger.warning("Check {} failed: {}", check.name, check_result.message)
            return self._should_stop_on_failure(check, stage_name, fail_fast)

    def _should_stop_on_failure(self, check: ReadinessCheck, stage_name: str, fail_fast: bool = False) -> tuple[bool, str]:
        """Determine if stage should stop due to check failure.

        Args:
            check: The check that failed
            stage_name: Name of the stage
            fail_fast: Whether the stage should stop on first failure

        Returns:
            tuple: (should_stop: bool, stop_reason: str)
        """
        # Stop stage execution if critical check fails
        if check.is_critical:
            logger.error("Critical check {} failed, stopping stage", check.name)
            return True, f"Critical check '{check.name}' failed in stage '{stage_name}'"

        # Stop stage execution on first failure if fail_fast is enabled
        if fail_fast:
            logger.warning("Stage failing fast due to {}", check.name)
            return True, f"Stage '{stage_name}' failed on check '{check.name}'"

        return False, ""

    def finalize_stage_result(self, result: ReadinessStageResult, stage_name: str) -> None:
        """Set final stage status if still running.

        Args:
            result: The stage result to finalize
            stage_name: Name of the stage
        """
        if result.status == CheckStatus.RUNNING:
            if result.failed_checks == 0:
                result.status = CheckStatus.SUCCESS
                result.message = (
                    f"Stage '{stage_name}' completed successfully: {result.successful_checks}/{result.total_checks} checks passed"
                )
            else:
                result.status = CheckStatus.FAILED
                result.message = (
                    f"Stage '{stage_name}' completed with failures: {result.failed_checks}/{result.total_checks} checks failed"
                )

    def mark_remaining_checks_skipped(
        self,
        result: ReadinessStageResult,
        failed_check: ReadinessCheck,
        all_checks: list[ReadinessCheck],
        stage_name: str,
        reason: str = "due to previous failure in stage",
    ):
        """Mark remaining checks as skipped.

        Args:
            result: The stage result to update
            failed_check: The check that caused the stage to stop
            all_checks: All checks in the stage
            stage_name: Name of the stage
            reason: The reason why checks are being skipped
        """
        try:
            failed_index = next(i for i, check in enumerate(all_checks) if check == failed_check)
        except StopIteration:
            # This shouldn't happen, but handle gracefully
            logger.warning("Could not find check {}", failed_check.name)
            return

        # Mark remaining checks as skipped
        for check in all_checks[failed_index + 1 :]:
            skipped_result = ReadinessCheckResult(
                status=CheckStatus.SKIPPED,
                message=f"Skipped {reason}",
                check_name=check.name,
                stage_name=stage_name,  # Add stage name for traceability
            )
            result.check_results.append(skipped_result)
            result.skipped_checks += 1
            logger.debug("Skipping check {} {}", check.name, reason)
