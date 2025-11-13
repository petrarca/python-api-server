"""Main pipeline implementation for orchestrating self-check stages.

This module provides the ReadinessPipeline class, which serves as the primary
interface for executing readiness checks in a structured, stage-based approach.
The pipeline manages server state, tracks execution results, and coordinates
the overall readiness assessment process.

Key Features:
- Stage-based execution orchestration
- Server state management (STARTING/CHECKING/OPERATIONAL/DEGRADED/ERROR)
- Result tracking and history management
- Integration with executor and calculator components
- Support for forced re-execution and caching

Typical Usage:
    pipeline = ReadinessPipeline([
        DatabaseValidationStage(),
        ServiceInitializationStage(),
        HealthCheckStage()
    ])

    result = pipeline.execute(force_rerun=True)
    if result.server_state == ServerState.OPERATIONAL:
        print("System is ready for traffic")
"""

import time

from loguru import logger

from .base import CheckStatus, ReadinessCheck, ReadinessPipelineResult, ServerState
from .calculator import ResultCalculator
from .executor import PipelineExecutor
from .stage import ReadinessStage, ReadinessStageResult


class ReadinessPipeline:
    """Pipeline that orchestrates execution of check stages in sequence.

    The ReadinessPipeline is the main entry point for running readiness checks.
    It manages the overall execution flow, maintains server state, and provides
    access to execution results. The pipeline coordinates between the executor
    for running stages and the calculator for finalizing results.

    This class provides:
    - Stage orchestration and execution management
    - Server state tracking throughout the pipeline lifecycle
    - Result history and current execution tracking
    - Integration with extracted executor and calculator components

    Attributes:
        stages: List of ReadinessStage objects to execute in order
        current_state: Current ServerState of the pipeline
        last_result: Most recent completed pipeline execution result
        current_result: Currently executing pipeline result (if any)
    """

    def __init__(self, stages: list[ReadinessStage]):
        """Initialize the pipeline with stages and components.

        Args:
            stages: List of pipeline stages to execute in order
        """
        self.stages = stages
        self.current_state = ServerState.STARTING
        self.last_result: ReadinessPipelineResult | None = None
        self.current_result: ReadinessPipelineResult | None = None  # Track in-progress execution

        # Initialize extracted components
        self._executor = PipelineExecutor()
        self._calculator = ResultCalculator()

    def execute(self, force_rerun: bool = False) -> ReadinessPipelineResult:
        """Execute the complete pipeline and return finalized results.

        Coordinates the execution of all stages using the executor component,
        then finalizes the results using the calculator component. Manages
        server state transitions and result tracking throughout the process.

        Args:
            force_rerun: If True, ignore all run_once caches and execute everything

        Returns:
            ReadinessPipelineResult: Complete pipeline execution result with
                finalized server state and aggregated statistics
        """
        logger.info("Starting readiness pipeline execution")
        start_time = time.time()

        self.current_state = ServerState.CHECKING

        # Use executor to run the pipeline
        result = self._executor.execute_pipeline(self.stages, force_rerun)

        # Set current_result to track in-progress execution
        self.current_result = result

        # Use calculator to finalize the result
        result = self._calculator.finalize_result(result, start_time)

        self.current_state = result.server_state
        self.last_result = result

        logger.info(f"Pipeline completed with status {result.overall_status.value} and server state {result.server_state.value}")
        return result

    def rerun(self) -> ReadinessPipelineResult:
        """Force re-execution of the entire pipeline, ignoring all run_once caches.

        This is a convenience method equivalent to execute(force_rerun=True).

        Returns:
            ReadinessPipelineResult: Complete pipeline execution result
        """
        return self.execute(force_rerun=True)

    def get_current_state(self) -> ServerState:
        """Get current pipeline state without running checks.

        Returns:
            ServerState: Current server state
        """
        return self.current_state

    def get_last_result(self) -> ReadinessPipelineResult | None:
        """Get the last pipeline execution result.

        Returns:
            Optional result of the last pipeline execution
        """
        return self.last_result

    def get_stage_names(self) -> list[str]:
        """Get names of all stages in this pipeline.

        Returns:
            List of stage names
        """
        return [stage.name for stage in self.stages]

    def get_stage(self, stage_name: str) -> ReadinessStage | None:
        """Get a stage by name.

        Args:
            stage_name: Name of the stage to retrieve

        Returns:
            The stage if found, None otherwise
        """
        return next((stage for stage in self.stages if stage.name == stage_name), None)

    def get_stage_result(self, stage_name: str) -> ReadinessStageResult | None:
        """Get the last execution result for a specific stage.

        Args:
            stage_name: Name of the stage to get result for

        Returns:
            The stage result if found, None otherwise
        """
        last_result = self.get_last_result()
        if not last_result:
            return None

        return next((stage_result for stage_result in last_result.stage_results if stage_result.stage_name == stage_name), None)

    def _get_stage_result_from_any_source(self, stage_name: str) -> ReadinessStageResult | None:
        """Get stage result from either current execution or final pipeline result.

        Works both during pipeline execution (using current_result) and after completion (using last_result).

        Args:
            stage_name: Name of the stage to get result for

        Returns:
            The stage result if found from any source, None otherwise
        """
        # Check current execution result first (handles running pipeline)
        if self.current_result:
            stage_result = next(
                (stage_result for stage_result in self.current_result.stage_results if stage_result.stage_name == stage_name),
                None,
            )
            if stage_result is not None:
                return stage_result

        # Fall back to final pipeline result (handles completed pipeline)
        if self.last_result:
            return next(
                (stage_result for stage_result in self.last_result.stage_results if stage_result.stage_name == stage_name),
                None,
            )

        return None

    def is_stage_successful(self, stage_name: str) -> bool:
        """Check if a specific stage completed successfully.

        This method works both during and after pipeline execution:
        - During execution: checks the current stage result
        - After execution: checks the final pipeline result

        Args:
            stage_name: Name of the stage to check

        Returns:
            True if stage was successful, False otherwise
        """
        stage_result = self._get_stage_result_from_any_source(stage_name)
        return stage_result is not None and stage_result.status == CheckStatus.SUCCESS

    def get_stage_status(self, stage_name: str) -> CheckStatus | None:
        """Get the status of a specific stage.

        This method works both during and after pipeline execution:
        - During execution: checks the current stage status
        - After execution: checks the final pipeline result

        Args:
            stage_name: Name of the stage to get status for

        Returns:
            The stage status if found, None otherwise
        """
        stage_result = self._get_stage_result_from_any_source(stage_name)
        return stage_result.status if stage_result else None

    def get_check(self, check_name: str) -> tuple[ReadinessStage | None, ReadinessCheck | None]:
        """Get a check by name across all stages.

        Args:
            check_name: Name of the check to retrieve

        Returns:
            Tuple of (stage, check) if found, (None, None) otherwise
        """
        for stage in self.stages:
            for check in stage.checks:
                if check.name == check_name:
                    return (stage, check)
        return (None, None)

    def reset(self) -> None:
        """Reset the execution state to initial conditions."""
        self.current_state = ServerState.STARTING
        self.last_result = None
        # Reset all stages in this pipeline
        for stage in self.stages:
            stage.reset()

    def __str__(self) -> str:
        """String representation of the pipeline."""
        return f"ReadinessPipeline(stages={len(self.stages)})"

    def __repr__(self) -> str:
        """Detailed representation of the pipeline."""
        stage_names = [stage.name for stage in self.stages]
        return f"ReadinessPipeline(stages={stage_names})"
