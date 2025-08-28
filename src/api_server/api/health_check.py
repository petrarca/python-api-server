"""Health check API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field

from api_server.self_check import ServerState
from api_server.services.health_check_service import HealthCheckService, get_health_check_service
from api_server.utils.version import VersionInfo

router = APIRouter(tags=["System"])


class CheckResultResponse(BaseModel):
    """Check result response model."""

    check: str = ""
    success: bool
    message: str
    details: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version_info: VersionInfo
    server_state: ServerState
    checks: list[CheckResultResponse] | None = Field(alias="checks", default=None)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "status": "ok",
                "version_info": {
                    "version": "0.1.0",
                    "full_version": "0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z",
                    "post_count": "11",
                    "git_commit": "a524f7b",
                    "is_dirty": True,
                    "build_timestamp": "2025-03-23T21:41:10Z",
                },
                "server_state": "operational",
                "checks": [
                    {
                        "check": "database_connection",
                        "success": True,
                        "message": "Database connection is healthy",
                        "details": {"status": "healthy", "connection": "active"},
                    }
                ],
            }
        }


# Define the dependencies as module-level variables
health_service_dependency = Depends(get_health_check_service)


@router.get("/health-check", response_model=HealthResponse)
async def health_check(health_service: HealthCheckService = health_service_dependency) -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: The health status of the API and database connection.
    """
    logger.debug("Health check requested")

    # Let the service handle all health checks, including database connection
    health_data = health_service.perform_health_check()

    # Convert the service response to the API response model
    response = HealthResponse(
        status=health_data["status"],
        version_info=health_data["version_info"],
        server_state=health_data["server_state"],
        checks=[CheckResultResponse(**check) for check in health_data["checks"]],
    )

    return response
