"""Metadata database connection health check for readiness pipeline."""

from loguru import logger
from pydantic import BaseModel

from api_server.database import borrow_db_session, is_healthy
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult
from api_server.settings import get_settings


class DatabaseHealth(BaseModel):
    connection: str | None = None
    error: str | None = None

    model_config = {
        "extra": "ignore",
    }

    def model_dump(self, **kwargs):
        """Custom serialization to exclude None error field."""
        data = super().model_dump(**kwargs)
        if data.get("error") is None:
            data.pop("error", None)
        return data


class DatabaseHealthCheck(ReadinessCheck):
    """Readiness check for database connection health."""

    def __init__(self, name: str = "database_health_check", is_critical: bool = True, run_once: bool = False):
        """Initialize the database connection check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
            run_once: Whether to cache the result (default: False, always re-check)
        """
        super().__init__(name, is_critical, run_once)

    def _execute(self) -> ReadinessCheckResult:
        """Check if the database connection is healthy.

        Returns:
            ReadinessCheckResult: The result of the check
        """
        logger.info("Checking database connection")

        try:
            # Access settings to get configuration values
            settings = get_settings()

            if not settings.database_url:
                return self.skip_stage(
                    "Database URL not configured - skipping database health check",
                    {"configured": False, "reason": "no_database_url"},
                )

            # Use a session to check database health
            with borrow_db_session() as session:
                health_result = is_healthy(session)

            if health_result.get("status") == "healthy":
                return self.success(
                    "Database connection is healthy",
                    {"connection": "active", "details": health_result},
                )
            else:
                return self.failed(
                    f"Database connection is unhealthy: {health_result.get('error', 'Unknown error')}",
                    {"connection": "unhealthy", "error": health_result.get("error")},
                )

        except Exception as e:
            logger.error(f"Error checking database connection: {str(e)}")
            return self.failed(
                f"Error checking database connection: {str(e)}",
                {"error": str(e), "type": type(e).__name__, "connection": "error"},
            )
