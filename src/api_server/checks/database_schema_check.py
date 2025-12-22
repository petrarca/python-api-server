"""Database schema validation check.

This check validates that the database schema is properly set up with alembic
and matches the expected head revision, without performing any migrations.
"""

from loguru import logger

from api_server.database import AlembicManager
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult


class DatabaseSchemaCheck(ReadinessCheck):
    """Check database schema status without performing migrations.

    Validates:
    - Alembic configuration exists
    - Alembic version table exists
    - Version record exists
    - Current version matches head revision

    This check never performs migrations - it only validates the current state.
    """

    def __init__(self, name: str = "database_schema", is_critical: bool = False, run_once: bool = False):
        """Initialize the database schema check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
            run_once: Whether to cache the result (default: False, always re-check for external changes)
        """
        super().__init__(name, is_critical, run_once)
        self.alembic_manager = AlembicManager()

    def _execute(self) -> ReadinessCheckResult:
        """Check database schema status without performing migrations."""
        try:
            logger.debug("Checking database schema status using AlembicManager")
            message, details, is_success = self.alembic_manager.validate_schema_state()

            if is_success:
                logger.info("Database schema validation passed")
                return self.success(message, details)
            else:
                logger.warning(f"Database schema validation failed: {message}")
                return self.failed(message, details)

        except (OSError, ValueError, RuntimeError, AttributeError) as e:
            logger.error(f"Error checking database schema: {str(e)}")
            return self.failed(f"Error checking database schema: {str(e)}", {"error": str(e), "type": type(e).__name__})
