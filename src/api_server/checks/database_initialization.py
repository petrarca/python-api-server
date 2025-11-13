"""Database initialization health check for readiness pipeline."""

from loguru import logger

from api_server.database import init_db, is_initialized
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult
from api_server.settings import get_settings


class DatabaseInitializationCheck(ReadinessCheck):
    """Readiness check for database initialization."""

    def __init__(self, name: str = "db_initialization", is_critical: bool = True):
        """Initialize the database initialization check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
        """
        super().__init__(name, is_critical, run_once=True)

    def _execute(self) -> ReadinessCheckResult:
        """Initialize the database connection and schema.

        Returns:
            ReadinessCheckResult: The result of the check
        """
        logger.info("Initializing database connection and schema")

        # Access settings to get configuration values
        settings = get_settings()

        if not settings.database_url:
            return self.skip_stage(
                "Database URL not configured - skipping all database checks",
                {"configured": False, "reason": "no_database_url"},
            )

        try:
            if not is_initialized():
                init_db()

            return self.success("Database initialized successfully", {"initialized": True})
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return self.failed(
                f"Database initialization failed: {str(e)}",
                {"error": str(e), "type": type(e).__name__, "initialized": False},
            )
