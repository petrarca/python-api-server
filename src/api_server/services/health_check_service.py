"""Health check service module."""

from functools import lru_cache
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from api_server.checks import get_readiness_pipeline
from api_server.profile import get_active_profiles
from api_server.readiness_pipeline import CheckStatus, ReadinessCheckResult, ServerState
from api_server.utils.version import get_version


class HealthCheckResult(BaseModel):
    """Pydantic model representing the full health check response."""

    model_config = {"use_enum_values": True}

    status: str
    server_state: ServerState
    active_profiles: list[str] = Field(default_factory=list)
    version_info: dict[str, Any] = Field(default_factory=dict)
    checks: list[ReadinessCheckResult] = Field(default_factory=list)


class HealthCheckService:
    """Service for performing health checks on the application."""

    def __init__(self):
        """Initialize the health check service with the default pipeline."""
        self._pipeline = get_readiness_pipeline()

    @property
    def pipeline(self):
        """Get the readiness pipeline for external access.

        Returns:
            The readiness pipeline instance.
        """
        return self._pipeline

    def get_server_state(self) -> ServerState:
        """Get the current state of the server.

        Returns:
            The current server state.
        """
        return self._pipeline.get_current_state()

    def get_check_results(self) -> HealthCheckResult:
        """Get the last results of all server readiness checks.

        Returns:
            The results of the last performed server readiness checks.
        """
        # Get last result from pipeline, return empty if no results yet
        last_result = self._pipeline.get_last_result()

        if last_result is None:
            # No previous results - return empty result with starting state
            active_profiles = sorted(get_active_profiles())
            return HealthCheckResult(
                status="error",
                server_state=ServerState.STARTING,
                active_profiles=active_profiles,
                version_info=get_version().model_dump(),
                checks=[],
            )

        # Convert the last pipeline result to health check response
        return self._to_health_check_response(last_result)

    def perform_health_check(self, force_rerun: bool = False) -> HealthCheckResult:
        """Perform a complete health check.

        This method handles all health checks, including database connection,
        and returns a formatted response.

        Args:
            force_rerun: If True, force re-execution of run_once checks

        Returns:
            A dictionary containing the complete health check response.
        """

        try:
            return self._run_self_checks(force_rerun=force_rerun)
        except Exception as e:  # pragma: no cover - defensive path
            logger.warning(f"Health check failed: {str(e)}")
            return HealthCheckResult(status="error", server_state=ServerState.ERROR, version_info={}, checks=[])

    def _run_self_checks(self, force_rerun: bool = False) -> HealthCheckResult:
        """Run all server readiness checks using an acquired db handle.

        Args:
            force_rerun: If True, force re-execution of run_once checks
        """
        if force_rerun:
            logger.info("Running server readiness checks (force rerun)")
        else:
            logger.info("Running server readiness checks")

        try:
            # Execute pipeline and get results
            result = self._pipeline.execute(force_rerun=force_rerun)
            return self._to_health_check_response(result)

        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error running server readiness checks: {str(e)}")
            return self._health_check_failed()

    def _health_check_failed(self) -> HealthCheckResult:
        """Return a HealthCheckResult indicating failure."""
        active_profiles = sorted(get_active_profiles())
        return HealthCheckResult(
            status="error",
            server_state=ServerState.ERROR,
            active_profiles=active_profiles,
            version_info={},
            checks=[],
        )

    def _to_health_check_response(self, pipeline_result) -> HealthCheckResult:
        """Convert health check results to a response format.

        Args:
            pipeline_result: The pipeline execution result.

        Returns:
            A dictionary containing the health response.
        """
        # Use pipeline result's server state
        server_state = pipeline_result.server_state

        # Flatten all check results from all stages
        all_check_results = []
        for stage_result in pipeline_result.stage_results:
            all_check_results.extend(stage_result.check_results)

        # Get the first check (GraphDB) for backward compatibility
        cdb_check = all_check_results[0] if all_check_results else None
        if cdb_check is None:
            server_state = ServerState.ERROR

        # Determine status based on overall success and critical checks
        status = (
            "ok"
            if (server_state == ServerState.OPERATIONAL and cdb_check is not None and cdb_check.status == CheckStatus.SUCCESS)
            else "error"
        )

        # Get version information
        version_info = get_version().model_dump()

        # Get active profiles
        active_profiles = sorted(get_active_profiles())

        return HealthCheckResult(
            status=status,
            server_state=server_state,
            active_profiles=active_profiles,
            version_info=version_info,
            checks=all_check_results,
        )


@lru_cache
def get_health_check_service() -> HealthCheckService:
    """Return cached process-wide ``HealthCheckService`` (singleton)."""
    return HealthCheckService()
