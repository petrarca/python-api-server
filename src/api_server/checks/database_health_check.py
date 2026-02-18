"""Metadata database connection health check for readiness pipeline."""

from loguru import logger
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import text

from api_server.database import borrow_db_session
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult


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
    """Readiness check for operational database connection health."""

    def __init__(self, name: str = "database_health_check", is_critical: bool = True, run_once: bool = False):
        """Initialize the operational database connection check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
            run_once: Whether to cache the result (default: False, always re-check)
        """
        super().__init__(name, is_critical, run_once)

    def _execute(self) -> ReadinessCheckResult:
        """Check if the operational database connection is healthy.

        Returns:
            ReadinessCheckResult: The result of the check
        """
        logger.info("Checking operational database connection")
        try:
            with borrow_db_session() as session:
                # Execute a simple query to check database connectivity
                result = session.exec(text("SELECT 1"))
                row = result.one()

                # Extract the value from the SQLAlchemy Row object
                actual_value = row[0]
                expected_value = 1

                if actual_value != expected_value:
                    error_msg = f"Expected result {expected_value}, but got {actual_value}"
                    db_health = DatabaseHealth(error=error_msg, connection="failed")
                    return self.failed(
                        f"Operational database connection is unhealthy: {error_msg}",
                        db_health.model_dump(),
                    )

                # Connection is healthy
                db_health = DatabaseHealth(connection="active")
                return self.success(
                    "Operational database connection is healthy",
                    db_health.model_dump(),
                )

        except (SQLAlchemyError, OSError, RuntimeError) as e:
            logger.error("Error checking operational database connection: {}", str(e))
            db_health = DatabaseHealth(error=str(e), connection="failed")
            return self.failed(
                f"Error checking operational database connection: {str(e)}",
                db_health.model_dump(),
            )
