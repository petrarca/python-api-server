"""Database version health check for readiness pipeline."""

import os

import alembic.config
import alembic.script
from alembic.runtime.migration import MigrationContext
from loguru import logger

from api_server.database import borrow_db_session
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult


class DatabaseVersionCheck(ReadinessCheck):
    """Readiness check for database migration version."""

    def __init__(self, name: str = "db_version", is_critical: bool = False, run_once: bool = False):
        """Initialize the database version check.

        Args:
            name: Name of this check
            is_critical: Whether failure should stop the pipeline stage
            run_once: Whether to cache the result (default: False, always re-check for external migrations)
        """
        super().__init__(name, is_critical, run_once)
        try:
            alembic_ini_path = os.path.join(os.getcwd(), "alembic.ini")
            self.alembic_cfg = alembic.config.Config(alembic_ini_path)
        except Exception as e:
            logger.error("Failed to initialize alembic configuration: {}", str(e))
            self.alembic_cfg = None

    def _execute(self) -> ReadinessCheckResult:
        """Check if the database version matches the expected version.

        Returns:
            ReadinessCheckResult: The result of the check
        """
        logger.info("Checking database version")
        try:
            if not self.alembic_cfg:
                return self.failed("Alembic configuration not initialized", {"error": "Alembic configuration not initialized"})

            with borrow_db_session() as session:
                # Get current database version
                connection = session.get_bind().connect()
                migration_context = MigrationContext.configure(connection)
                current_rev = migration_context.get_current_revision()

                # Get expected head revision from alembic
                script_directory = alembic.script.ScriptDirectory.from_config(self.alembic_cfg)
                head_rev = script_directory.get_current_head()

                if current_rev == head_rev:
                    return self.success(
                        "Database is at the latest migration version",
                        {"current_revision": current_rev, "head_revision": head_rev, "is_latest": True},
                    )
                else:
                    return self.failed(
                        "Database is not at the latest migration version",
                        {"current_revision": current_rev, "head_revision": head_rev, "is_latest": False},
                    )
        except Exception as e:
            logger.error("Error checking database version: {}", e)
            return self.failed(f"Error checking database version: {str(e)}", {"error": str(e), "type": type(e).__name__})
