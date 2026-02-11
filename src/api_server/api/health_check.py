"""Health Check API - Service health and database connectivity status.

This module provides the health check endpoint that:
- Verifies API service is running
- Tests database connectivity
- Reports component status

Used for monitoring, load balancers, and operational health checks.
"""

from fastapi import APIRouter, Depends, Query
from loguru import logger

from api_server.services.health_check_service import HealthCheckResult, HealthCheckService, get_health_check_service

router = APIRouter(tags=["System"])


# Define the dependencies as module-level variables
health_service_dependency = Depends(get_health_check_service)


@router.get("/health-check", response_model=HealthCheckResult)
async def health_check(
    health_service: HealthCheckService = health_service_dependency,
) -> HealthCheckResult:
    """
    Get the last cached health check results (fast, read-only).

    Returns the results from the most recent health check execution without
    running the checks again. This is suitable for:
    - Monitoring systems that poll frequently
    - Load balancer health checks
    - Dashboard displays

    Args:
        health_service: Health check service (injected)

    Returns:
        HealthCheckResult object containing:
        - status: Overall health status ("ok" or "error")
        - server_state: Current server state
        - active_profiles: List of enabled API profiles (REST, GraphQL, MCP)
        - version_info: Server version information
        - checks: List of individual check results

    Example:
        GET /health-check
        Returns: {
            "status": "ok",
            "server_state": "operational",
            "active_profiles": ["GraphQL", "REST"],
            "version_info": {...},
            "checks": [...]
        }

    Note:
        - Returns HTTP 200 even if unhealthy (status in response body)
        - Returns cached results from last execution (fast)
        - To trigger fresh execution, use POST /health-check
    """
    logger.debug("Health check requested (cached results)")

    # Return last cached results
    return health_service.get_check_results()


@router.post("/health-check", response_model=HealthCheckResult)
async def trigger_health_check(
    force_rerun: bool = Query(False, description="Force re-execution of run_once checks"),
    health_service: HealthCheckService = health_service_dependency,
) -> HealthCheckResult:
    """
    Execute health checks and return fresh results.

    Triggers execution of the complete readiness pipeline:
    - Database initialization and health
    - Alembic migration status
    - Database version check

    Use this endpoint when you need current state, such as:
    - After running database migrations
    - Manual health verification
    - Troubleshooting issues
    - Forcing re-check of external dependencies

    Args:
        force_rerun: If True, force re-execution of run_once checks
        health_service: Health check service (injected)

    Returns:
        HealthCheckResult object with fresh check results

    Example:
        POST /health-check
        POST /health-check?force_rerun=true

    Note:
        - Executes all health checks (may take longer than GET)
        - Updates cached results for subsequent GET requests
        - Checks with run_once=True will return cached results unless force_rerun=True
        - Checks with run_once=False will always execute fresh
    """
    logger.info(f"Health check execution triggered via POST (force_rerun={force_rerun})")

    # Execute pipeline and return fresh results
    return health_service.perform_health_check(force_rerun=force_rerun)
