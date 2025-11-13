"""Pipeline execution orchestration components.

This module provides the PipelineExecutor class responsible for orchestrating
the execution of readiness pipelines. It manages stage execution order,
handles critical stage failures, and coordinates the overall pipeline flow.

Key Features:
- Sequential stage execution with proper ordering
- Critical stage failure handling and pipeline termination
- Comprehensive logging and progress tracking
- Exception handling with graceful degradation
- Stage skipping on critical failures
"""

import time

import arrow
from loguru import logger

from .base import CheckStatus, ReadinessPipelineResult, ReadinessStageResult, ServerState
from .stage import ReadinessStage


class PipelineExecutor:
    """Handles the execution logic for readiness pipelines.

    The PipelineExecutor orchestrates the execution of pipeline stages in sequence,
    managing the overall flow and handling critical failures. It provides the main
    entry point for running readiness checks and ensures proper error handling
    and logging throughout the execution process.

    Attributes:
        None (stateless executor - manages execution flow only)
    """

    def execute_pipeline(self, stages: list[ReadinessStage], force_rerun: bool = False) -> ReadinessPipelineResult:
        """Execute the complete pipeline sequentially.

        Orchestrates the execution of all pipeline stages in order, handling
        critical failures and managing the overall pipeline state. The executor
        will stop execution if a critical stage fails and mark remaining stages
        as skipped.

        Args:
            stages: List of pipeline stages to execute in order
            force_rerun: If True, ignore all run_once caches and execute everything

        Returns:
            ReadinessPipelineResult: Complete pipeline execution result with
                stage results, overall status, and execution timing
        """
        logger.info("Starting readiness pipeline execution")
        start_time = time.time()
        executed_at = arrow.utcnow().isoformat()

        result = ReadinessPipelineResult(
            server_state=ServerState.CHECKING,
            overall_status=CheckStatus.RUNNING,
            message="Self-check pipeline execution in progress",
            executed_at=executed_at,
        )

        try:
            execution_order = self._get_execution_order(stages)
            logger.info(f"Pipeline will execute {len(execution_order)} stages")

            for stage in execution_order:
                logger.info(f"Executing stage: {stage.name}")
                stage_result = stage.execute(force_rerun=force_rerun)
                result.stage_results.append(stage_result)

                # Log stage completion
                if stage_result.status == CheckStatus.SUCCESS:
                    logger.info(f"Stage {stage.name} completed successfully")
                elif stage_result.status == CheckStatus.SKIPPED:
                    logger.info(f"Stage {stage.name} was skipped")
                else:
                    logger.warning(f"Stage {stage.name} failed")

                # Stop pipeline if critical stage fails
                if stage.is_critical and stage_result.status == CheckStatus.FAILED:
                    result.overall_status = CheckStatus.FAILED
                    result.server_state = ServerState.ERROR
                    result.message = f"Critical stage '{stage.name}' failed"
                    logger.error(f"Critical stage {stage.name} failed, stopping")
                    self._mark_remaining_stages_skipped(result, stage, stages)
                    break

        except Exception as e:
            logger.error(f"Pipeline execution failed with exception: {e}")
            result.overall_status = CheckStatus.FAILED
            result.server_state = ServerState.ERROR
            result.message = f"Pipeline execution failed: {str(e)}"
            result.total_execution_time_ms = (time.time() - start_time) * 1000

        return result

    def _get_execution_order(self, stages: list[ReadinessStage]) -> list[ReadinessStage]:
        """Get stages in execution order (maintain original order).

        Currently maintains the original order in which stages were added
        to the pipeline. This method exists to allow for future extensions
        such as dependency-based ordering or priority sorting.

        Args:
            stages: List of stages to order

        Returns:
            List of stages in the order they were added to the pipeline
        """
        return stages

    def _mark_remaining_stages_skipped(
        self,
        result: ReadinessPipelineResult,
        failed_stage: ReadinessStage,
        all_stages: list[ReadinessStage],
    ):
        """Mark remaining stages as skipped after a critical stage failure.

        When a critical stage fails, all subsequent stages are marked as
        skipped to maintain pipeline integrity and provide clear visibility
        into what was not executed due to the failure.

        Args:
            result: Pipeline result to update with skipped stage results
            failed_stage: The stage that caused the pipeline to stop
            all_stages: All stages in the pipeline (for finding remaining ones)
        """
        try:
            failed_index = next(i for i, stage in enumerate(all_stages) if stage == failed_stage)
        except StopIteration:
            logger.warning(f"Could not find failed stage {failed_stage.name}")
            return

        # Mark remaining stages as skipped
        for stage in all_stages[failed_index + 1 :]:
            skipped_result = ReadinessStageResult(
                stage_name=stage.name,
                status=CheckStatus.SKIPPED,
                message="Skipped due to critical stage failure",
                total_checks=len(stage.checks),
                skipped_checks=len(stage.checks),
                run_once=stage.run_once,
            )
            result.stage_results.append(skipped_result)
            logger.info(f"Skipping stage {stage.name} due to critical failure")
