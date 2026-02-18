"""Alembic database setup health check for readiness pipeline."""

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from api_server.database import borrow_db_session
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult


class AlembicSetupCheck(ReadinessCheck):
    """Readiness check for Alembic database setup."""

    def __init__(self, name: str = "alembic_setup", is_critical: bool = False, run_once: bool = False):
        """Initialize the Alembic setup check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
            run_once: Whether to cache the result (default: False, always re-check for external migrations)
        """
        super().__init__(name, is_critical, run_once)

    def _execute(self) -> ReadinessCheckResult:
        """Check if the database is set up with alembic.

        Returns:
            ReadinessCheckResult: The result of the check
        """
        logger.info("Checking alembic setup")
        try:
            with borrow_db_session() as session:
                # Check if alembic_version table exists using Inspector.has_table()
                # Create fresh Inspector each time to bypass any caching and reflect current DB state
                # This works database-agnostically (PostgreSQL, MySQL, SQLite, etc.)
                logger.debug("Creating fresh Inspector instance to check table existence")
                inspector = inspect(session.get_bind())
                has_alembic_table = inspector.has_table("alembic_version")
                logger.debug("Inspector.has_table('alembic_version') returned: {}", has_alembic_table)

                if has_alembic_table:
                    logger.debug("Table exists, checking for version data")
                    # Check if the table has the expected structure
                    result = session.exec(text("SELECT version_num FROM alembic_version LIMIT 1"))
                    version_exists = result.one_or_none() is not None

                    if version_exists:
                        return self.success(
                            "Database is properly set up with alembic", {"has_alembic_table": True, "has_version": True}
                        )
                    else:
                        msg = "Alembic version table exists but contains no version"
                        return self.failed(msg, {"has_alembic_table": True, "has_version": False})
                else:
                    msg = "Database is not set up with alembic (table not found)"
                    return self.failed(msg, {"has_alembic_table": False})
        except (SQLAlchemyError, OSError, ValueError, RuntimeError) as e:
            logger.error("Error checking alembic setup: {}", str(e))
            return self.failed(f"Error checking alembic setup: {str(e)}", {"error": str(e), "type": type(e).__name__})
