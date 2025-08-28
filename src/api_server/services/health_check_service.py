"""Health check service module."""

from typing import Any

from loguru import logger
from sqlmodel import Session

from api_server.database import get_db_session, is_healthy
from api_server.self_check import CheckResult, ServerState, server_self_check
from api_server.utils.version import get_version


class HealthCheckService:
    """Service for performing health checks on the application."""

    def check_database_health(self, session: Session) -> dict[str, Any]:
        """Check if the database connection is healthy.

        Args:
            session: The database session to use for the health check.

        Returns:
            A dictionary containing the database health status and connection info.
        """
        return is_healthy(session)

    def get_server_state(self) -> ServerState:
        """Get the current state of the server.

        Returns:
            The current server state.
        """
        return server_self_check.get_state()

    def get_check_results(self) -> list[CheckResult]:
        """Get the results of all server self-checks.

        Returns:
            The results of all server self-checks.
        """
        return server_self_check.get_check_results()

    def run_self_checks(self, session: Session) -> bool:
        """Run all server self-checks.

        Args:
            session: The database session to use for the checks.

        Returns:
            True if all checks passed, False otherwise.
        """
        logger.info("Running server self-checks")
        try:
            return server_self_check.run_self_checks(session)
        except Exception as e:
            logger.error(f"Error running server self-checks: {str(e)}")
            return False

    def to_health_response(self, db_health: dict[str, Any]) -> dict[str, Any]:
        """Convert health check results to a response format.

        Args:
            db_health: The database health check result.

        Returns:
            A dictionary containing the health response.
        """
        server_state = server_self_check.get_state()
        check_results = server_self_check.get_check_results()

        # Override server state if database is down
        if db_health["status"] != "healthy":
            server_state = ServerState.ERROR

        # Status is "ok" if server is operational and database is healthy
        status = "ok" if server_state == ServerState.OPERATIONAL and db_health["status"] == "healthy" else "error"

        # Start with the database connection check
        formatted_checks = self._format_db_connection_check(db_health)

        # If database connection is healthy, add other checks
        if db_health["status"] == "healthy" and check_results:
            self._add_remaining_checks(formatted_checks, check_results)

        # Get version information
        version_info = get_version()

        response = {
            "status": status,
            "version_info": version_info.model_dump(),
            "server_state": server_state,
            "checks": formatted_checks,
        }

        return response

    def _format_db_connection_check(self, db_health: dict[str, Any]) -> list[dict[str, Any]]:
        """Format the database connection check.

        Args:
            db_health: The database health check result.

        Returns:
            A list containing the formatted database connection check.
        """
        db_check = {
            "check": "database_connection",
            "success": db_health["status"] == "healthy",
            "message": "Database connection is healthy"
            if db_health["status"] == "healthy"
            else f"Database connection is unhealthy: {db_health.get('error', 'Unknown error')}",
            "details": db_health,
        }
        return [db_check]

    def _add_remaining_checks(self, formatted_checks: list[dict[str, Any]], check_results: list[CheckResult]) -> None:
        """Add remaining checks to the formatted checks list.

        Args:
            formatted_checks: The list of formatted checks to add to.
            check_results: The check results to format and add.
        """
        # Create a mapping of check types to their results
        check_map = {result.check: result for result in check_results if result.check != "database_connection"}

        # Process checks in sequence, stopping if any check fails

        # Step 1: Alembic setup check
        if "alembic_setup" in check_map:
            result = check_map["alembic_setup"]
            alembic_check = self._format_check_result(result)
            formatted_checks.append(alembic_check)

            # If alembic setup failed, don't include any subsequent checks
            if not result.success:
                logger.warning("Alembic setup check failed, skipping remaining checks")
                return
        else:
            # If alembic setup check doesn't exist, we can't proceed with database version check
            logger.warning("Alembic setup check not found, skipping remaining checks")
            return

        # Step 2: Database version check (only run if alembic setup succeeded)
        if "database_version" in check_map:
            result = check_map["database_version"]
            db_version_check = self._format_check_result(result)
            formatted_checks.append(db_version_check)

            # If database version check failed, don't include any subsequent checks
            if not result.success:
                logger.warning("Database version check failed, skipping remaining checks")
                return

        # Step 3: Any remaining checks (only run if all previous checks succeeded)
        for check_name, result in check_map.items():
            if check_name not in ["alembic_setup", "database_version"]:
                formatted_checks.append(self._format_check_result(result))

                # If this check failed, don't include any subsequent checks
                if not result.success:
                    logger.warning(f"{check_name} check failed, skipping remaining checks")
                    return

    def _format_check_result(self, result: CheckResult) -> dict[str, Any]:
        """Format a check result.

        Args:
            result: The check result to format.

        Returns:
            A dictionary containing the formatted check result.
        """
        return {
            "check": result.check,
            "success": result.success,
            "message": result.message,
            "details": result.details,
        }

    def perform_health_check(self) -> dict[str, Any]:
        """Perform a complete health check.

        This method handles all health checks, including database connection,
        and returns a formatted response.

        Returns:
            A dictionary containing the complete health check response.
        """
        try:
            # Try to get a database session
            session = next(get_db_session())

            # If we get here, the database connection is successful
            db_health = self.check_database_health(session)

            # Run self-checks to populate check_results
            self.run_self_checks(session)

            # Format the response
            return self.to_health_response(db_health)
        except Exception as e:
            # Handle any database connection failures
            logger.warning(f"Database connection failed during health check: {str(e)}")

            # Create a failed database connection check
            db_check = {
                "check": "database_connection",
                "success": False,
                "message": "Database connection failed",
                "details": {"error": str(e), "status": "unhealthy", "database_url": "unknown", "connection": "failed"},
            }

            # Return a health response with just the failed database check
            version_info = get_version()
            return {
                "status": "error",
                "version_info": version_info.model_dump(),
                "server_state": ServerState.ERROR,
                "checks": [db_check],
            }


# Singleton instance getter
def get_health_check_service() -> HealthCheckService:
    """Get or create a HealthCheckService instance.

    Returns:
        A HealthCheckService instance.
    """
    return HealthCheckService()
