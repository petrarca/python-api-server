"""Server state registry for breaking circular dependencies.

This module provides a lightweight, dependency-free registry for holding
the current server state and readiness check results. It allows low-level
services (like OpsDbServiceBase) to check system status without importing
the heavy HealthCheckService or ReadinessPipeline, thus preventing
import cycles.
"""

from functools import lru_cache

from .readiness_pipeline.enums import CheckStatus, ServerState
from .readiness_pipeline.models import ReadinessPipelineResult, ReadinessStageResult


class ServerStateRegistry:
    """Registry for holding current server state and stage results.

    This class is a singleton that serves as a shared state container.
    The ReadinessPipeline writes to it, and services read from it.
    """

    def __init__(self):
        self._server_state: ServerState = ServerState.STARTING
        self._stage_statuses: dict[str, CheckStatus] = {}
        self._stage_results: dict[str, ReadinessStageResult] = {}
        self._last_pipeline_result: ReadinessPipelineResult | None = None

    @property
    def server_state(self) -> ServerState:
        """Get the current server state."""
        return self._server_state

    def set_server_state(self, state: ServerState) -> None:
        """Set the current server state.

        Args:
            state: New server state
        """
        self._server_state = state

    def update_stage_status(self, stage_name: str, status: CheckStatus, result: ReadinessStageResult | None = None) -> None:
        """Update the status and result of a pipeline stage.

        Args:
            stage_name: Name of the stage (e.g., "database", "config")
            status: Status of the stage (SUCCESS, FAILURE, etc.)
            result: Optional result object from the stage
        """
        self._stage_statuses[stage_name] = status
        if result is not None:
            self._stage_results[stage_name] = result

    def is_stage_successful(self, stage_name: str) -> bool:
        """Check if a specific stage completed successfully.

        Args:
            stage_name: Name of the stage to check

        Returns:
            True if stage status is SUCCESS, False otherwise
        """
        return self._stage_statuses.get(stage_name) == CheckStatus.SUCCESS

    def get_stage_status(self, stage_name: str) -> CheckStatus | None:
        """Get the status of a specific stage.

        Args:
            stage_name: Name of the stage

        Returns:
            Stage status if available, None otherwise
        """
        return self._stage_statuses.get(stage_name)

    def reset(self) -> None:
        """Reset the registry to initial state."""
        self._server_state = ServerState.STARTING
        self._stage_statuses.clear()
        self._stage_results.clear()
        self._last_pipeline_result = None

    def get_last_pipeline_result(self) -> ReadinessPipelineResult | None:
        """Get the last pipeline execution result.

        Returns:
            The last ReadinessPipelineResult if available, None otherwise
        """
        return self._last_pipeline_result

    def set_last_pipeline_result(self, result: ReadinessPipelineResult) -> None:
        """Set the last pipeline execution result.

        Args:
            result: The pipeline result to store
        """
        self._last_pipeline_result = result


@lru_cache(maxsize=1)
def get_server_state_registry() -> ServerStateRegistry:
    """Get the singleton server state registry instance.

    Returns:
        The global server state registry
    """
    return ServerStateRegistry()
