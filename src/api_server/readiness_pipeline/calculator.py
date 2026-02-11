"""Pipeline result calculation and finalization components.

This module provides the ResultCalculator class responsible for aggregating results
from pipeline stage executions, calculating final statistics, and determining the
overall server state based on check outcomes.

Key Features:
- Aggregation of check and stage statistics across all pipeline stages
- Final server state determination (OPERATIONAL/DEGRADED/ERROR)
- Overall pipeline status calculation based on individual check results
- Total execution time measurement for performance monitoring

State Determination Logic:
- All checks pass: OPERATIONAL state with SUCCESS status
- Some checks pass: DEGRADED state with FAILED status
- No checks pass: ERROR state with FAILED status

Typical Usage:
    calculator = ResultCalculator()
    final_result = calculator.finalize_result(pipeline_result, start_time)

    if final_result.server_state == ServerState.OPERATIONAL:
        print("System is ready for traffic")
    elif final_result.server_state == ServerState.DEGRADED:
        print("System is ready but with limited functionality")
    else:
        print("System is not ready")

"""

import arrow
from loguru import logger

from .enums import CheckStatus, ServerState
from .models import ReadinessPipelineResult


class ResultCalculator:
    """Handles result calculation and finalization for readiness pipelines.

    The ResultCalculator is responsible for taking the raw results from pipeline
    execution and transforming them into a finalized, comprehensive result. It
    aggregates statistics from all stages and checks, determines the appropriate
    server state, and calculates overall execution metrics.

    This class provides the critical business logic for determining whether the
    system is ready to serve traffic based on the outcomes of all readiness checks
    across all pipeline stages.

    Attributes:
        None (stateless calculator - operates on result objects)

    Example:
        calculator = ResultCalculator()
        pipeline_result = ReadinessPipelineResult(...)
        start_time = arrow.utcnow().float_timestamp

        # Execute pipeline stages...

        final_result = calculator.finalize_result(pipeline_result, start_time)
        print(f"Server state: {final_result.server_state}")
        print(f"Total execution time: {final_result.total_execution_time_ms}ms")
    """

    def finalize_result(self, result: ReadinessPipelineResult, start_time: float) -> ReadinessPipelineResult:
        """Calculate final statistics and determine overall server state.

        This method performs the critical finalization step for pipeline execution.
        It aggregates statistics from all stage results, determines the appropriate
        server state based on check outcomes, and calculates total execution time.

        The finalization process follows these steps:
        1. Aggregate check statistics (total, successful, failed, skipped) from all stages
        2. Calculate stage statistics (total, successful, failed, skipped) from stage results
        3. Determine overall server state based on check success/failure patterns
        4. Calculate total pipeline execution time
        5. Update result message and log appropriate level messages

        Server State Logic:
        - OPERATIONAL: All checks passed successfully
        - DEGRADED: Some checks failed but at least one succeeded
        - ERROR: All checks failed or critical infrastructure checks failed

        Args:
            result: The ReadinessPipelineResult to finalize. Should contain
                   completed stage_results from pipeline execution.
            start_time: Unix timestamp (float) when pipeline execution began.
                       Used to calculate total execution time.

        Returns:
            ReadinessPipelineResult: The same result object, now finalized with:
                - Aggregated check and stage statistics
                - Determined server state (OPERATIONAL/DEGRADED/ERROR)
                - Final overall status (SUCCESS/FAILED)
                - Total execution time in milliseconds
                - Appropriate status message

        Example:
            calculator = ResultCalculator()
            result = ReadinessPipelineResult(
                server_state=ServerState.CHECKING,
                overall_status=CheckStatus.RUNNING,
                stage_results=[...],  # Completed stage results
            )

            final_result = calculator.finalize_result(result, arrow.utcnow().float_timestamp)

            if final_result.server_state == ServerState.OPERATIONAL:
                print("System is ready")
            elif final_result.server_state == ServerState.DEGRADED:
                print("System is ready but with limited functionality")
            else:
                print("System is not ready")
        """
        # Aggregate check and stage statistics from all stage results
        for stage_result in result.stage_results:
            result.total_checks += stage_result.total_checks
            result.successful_checks += stage_result.successful_checks
            result.failed_checks += stage_result.failed_checks
            result.skipped_checks += stage_result.skipped_checks

        # Recalculate stage totals from actual stage results to be sure
        result.total_stages = len(result.stage_results)
        result.successful_stages = sum(1 for sr in result.stage_results if sr.status == CheckStatus.SUCCESS)
        result.failed_stages = sum(1 for sr in result.stage_results if sr.status == CheckStatus.FAILED)
        result.skipped_stages = sum(1 for sr in result.stage_results if sr.status == CheckStatus.SKIPPED)

        # Set final status and state if still running
        if result.overall_status == CheckStatus.RUNNING:
            if result.failed_checks == 0:
                result.overall_status = CheckStatus.SUCCESS
                result.server_state = ServerState.OPERATIONAL
                result.message = "All pipeline stages completed successfully"
                logger.info("Pipeline completed successfully")
            else:
                result.overall_status = CheckStatus.FAILED
                # Determine if degraded (some success) or error (total failure)
                if result.successful_checks > 0:
                    result.server_state = ServerState.DEGRADED
                else:
                    result.server_state = ServerState.ERROR
                result.message = f"Pipeline completed with {result.failed_checks} check failures"
                logger.warning("Pipeline completed with {} failures", result.failed_checks)

        result.total_execution_time_ms = (arrow.utcnow().float_timestamp - start_time) * 1000
        return result
