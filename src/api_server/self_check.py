"""Server self-check module.

This module provides functionality to verify that the server is properly configured
and ready to operate. It performs checks in a specific order:
1. Database connection health
2. Alembic setup verification
3. Database migration version check
"""

import os
from enum import Enum
from typing import Any

import alembic.config
import alembic.runtime.migration
import alembic.script
from alembic.runtime.migration import MigrationContext
from loguru import logger
from sqlalchemy import inspect, text
from sqlmodel import Session

from api_server.database import is_healthy


class ServerState(str, Enum):
    """Enum representing the possible states of the server."""

    STARTING = "starting"
    CHECKING = "checking"
    OPERATIONAL = "operational"
    ERROR = "error"


class CheckResult:
    """Result of a self-check operation."""

    def __init__(self, success: bool, message: str, details: dict[str, Any] | None = None, check: str = ""):
        """Initialize a check result.

        Args:
            success: Whether the check was successful
            message: A human-readable message describing the result
            details: Optional additional details about the check result
            check: Identifier for the type of check performed
        """
        self.success = success
        self.message = message
        self.details = details or {}
        self.check = check


class ServerSelfCheck:
    """Server self-check functionality."""

    def __init__(self):
        """Initialize the self-check module."""
        self.state: ServerState = ServerState.STARTING
        self.check_results: list[CheckResult] = []
        self.alembic_cfg = None

        # Initialize alembic configuration
        try:
            self.alembic_cfg = alembic.config.Config(os.path.join(os.getcwd(), "alembic.ini"))
        except Exception as e:
            logger.error(f"Failed to initialize alembic configuration: {str(e)}")

    def run_self_checks(self, session: Session) -> bool:
        """Run all self-checks in the specified order.

        Args:
            session: The database session to use for checks

        Returns:
            bool: True if all checks passed, False otherwise
        """
        logger.info("Starting server self-check")
        self.state = ServerState.CHECKING
        self.check_results = []

        # Run all checks in sequence
        return self._run_check_sequence(session)

    def _run_check_sequence(self, session: Session) -> bool:
        """Run all checks in the proper sequence, stopping on first failure.

        Args:
            session: The database session to use for checks

        Returns:
            bool: True if all checks passed, False otherwise
        """
        all_checks_passed = True

        # Check 1: Database connection
        db_check_result = self._run_and_record_check_without_stopping(
            session, self.check_database_connection, "Database connection check failed"
        )
        if not db_check_result:
            # If database check fails, we can't run the other checks that depend on database access
            # But we don't want to stop the application from starting
            logger.warning("Skipping remaining checks due to database connection failure")
            return False

        # Check 2: Alembic setup
        alembic_check_result = self._run_and_record_check_without_stopping(
            session, self.check_alembic_setup, "Alembic setup check failed"
        )
        if not alembic_check_result:
            all_checks_passed = False

        # Check 3: Database version
        db_version_check_result = self._run_and_record_check_without_stopping(
            session, self.check_database_version, "Database version check failed"
        )
        if not db_version_check_result:
            all_checks_passed = False

        # Set server state based on check results
        if all_checks_passed:
            logger.success("All server self-checks passed")
            self.state = ServerState.OPERATIONAL
        else:
            logger.warning("Some server self-checks failed, but application will continue to start")
            self.state = ServerState.ERROR

        return all_checks_passed

    def _run_and_record_check(self, session: Session, check_function, failure_message: str) -> bool:
        """Run a single check, record its result, and handle failure logging.

        Args:
            session: The database session to use for the check
            check_function: The check function to run
            failure_message: Message to log if the check fails

        Returns:
            bool: True if the check passed, False otherwise
        """
        check_result = check_function(session)
        self.check_results.append(check_result)

        if not check_result.success:
            logger.error(failure_message)
            self.state = ServerState.ERROR
            return False

        return True

    def _run_and_record_check_without_stopping(self, session: Session, check_function, failure_message: str) -> bool:
        """Run a single check and record its result without stopping on failure.

        Args:
            session: The database session to use for the check
            check_function: The check function to run
            failure_message: Message to log if the check fails

        Returns:
            bool: True if the check passed, False otherwise
        """
        try:
            check_result = check_function(session)
            self.check_results.append(check_result)

            if not check_result.success:
                logger.warning(failure_message)
                return False

            return True
        except Exception as e:
            # Create a failure check result for the exception
            error_result = CheckResult(
                success=False, message=f"{failure_message}: {str(e)}", details={"error": str(e)}, check=check_function.__name__
            )
            self.check_results.append(error_result)
            logger.warning(f"{failure_message}: {str(e)}")
            return False

    def check_database_connection(self, session: Session) -> CheckResult:
        """Check if the database connection is healthy.

        Args:
            session: The database session to use for the check

        Returns:
            CheckResult: The result of the check
        """
        logger.info("Checking database connection")
        try:
            db_health = is_healthy(session)
            if db_health["status"] == "healthy":
                return CheckResult(
                    success=True, message="Database connection is healthy", details=db_health, check="database_connection"
                )
            else:
                return CheckResult(
                    success=False,
                    message=f"Database connection is unhealthy: {db_health.get('error', 'Unknown error')}",
                    details=db_health,
                    check="database_connection",
                )
        except Exception as e:
            logger.error(f"Error checking database connection: {str(e)}")
            return CheckResult(
                success=False,
                message=f"Error checking database connection: {str(e)}",
                details={"error": str(e)},
                check="database_connection",
            )

    def check_alembic_setup(self, session: Session) -> CheckResult:
        """Check if the database is set up with alembic.

        Args:
            session: The database session to use for the check

        Returns:
            CheckResult: The result of the check
        """
        logger.info("Checking alembic setup")
        try:
            # Check if alembic_version table exists
            inspector = inspect(session.get_bind())
            has_alembic_table = "alembic_version" in inspector.get_table_names()

            if has_alembic_table:
                # Check if the table has the expected structure
                result = session.exec(text("SELECT version_num FROM alembic_version LIMIT 1"))
                version_exists = result.one_or_none() is not None

                if version_exists:
                    return CheckResult(
                        success=True,
                        message="Database is properly set up with alembic",
                        details={"has_alembic_table": True, "has_version": True},
                        check="alembic_setup",
                    )
                else:
                    return CheckResult(
                        success=False,
                        message="Alembic version table exists but contains no version information",
                        details={"has_alembic_table": True, "has_version": False},
                        check="alembic_setup",
                    )
            else:
                return CheckResult(
                    success=False,
                    message="Database is not set up with alembic (alembic_version table not found)",
                    details={"has_alembic_table": False},
                    check="alembic_setup",
                )
        except Exception as e:
            logger.error(f"Error checking alembic setup: {str(e)}")
            return CheckResult(
                success=False, message=f"Error checking alembic setup: {str(e)}", details={"error": str(e)}, check="alembic_setup"
            )

    def check_database_version(self, session: Session) -> CheckResult:
        """Check if the database version matches the expected version.

        Args:
            session: The database session to use for the check

        Returns:
            CheckResult: The result of the check
        """
        logger.info("Checking database version")
        try:
            if not self.alembic_cfg:
                return CheckResult(
                    success=False,
                    message="Alembic configuration not initialized",
                    details={"error": "Alembic configuration not initialized"},
                    check="database_version",
                )

            # Get current database version
            connection = session.get_bind().connect()
            migration_context = MigrationContext.configure(connection)
            current_rev = migration_context.get_current_revision()

            # Get expected head revision from alembic
            script_directory = alembic.script.ScriptDirectory.from_config(self.alembic_cfg)
            head_rev = script_directory.get_current_head()

            if current_rev == head_rev:
                return CheckResult(
                    success=True,
                    message="Database is at the latest migration version",
                    details={"current_revision": current_rev, "head_revision": head_rev, "is_latest": True},
                    check="database_version",
                )
            else:
                return CheckResult(
                    success=False,
                    message="Database is not at the latest migration version",
                    details={"current_revision": current_rev, "head_revision": head_rev, "is_latest": False},
                    check="database_version",
                )
        except Exception as e:
            logger.error(f"Error checking database version: {e}")
            return CheckResult(
                success=False,
                message=f"Error checking database version: {e}",
                details={"error": str(e)},
                check="database_version",
            )

    def get_state(self) -> ServerState:
        """Get the current state of the server.

        Returns:
            ServerState: The current server state
        """
        return self.state

    def get_check_results(self) -> list[CheckResult]:
        """Get the results of all checks.

        Returns:
            List[CheckResult]: The results of all checks
        """
        return self.check_results


# Create a global instance of the ServerSelfCheck class
server_self_check = ServerSelfCheck()
