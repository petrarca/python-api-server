"""Pipeline builders for CLI operations.

This module provides CLI-specific pipeline stage builders.
These are separate from the server's pipeline builders because CLI operations
may need different check combinations (e.g., no auto-migration, basic checks only).
"""

from api_server.checks.database_health_check import DatabaseHealthCheck
from api_server.checks.database_initialization import DatabaseInitializationCheck
from api_server.checks.database_schema_check import DatabaseSchemaCheck
from api_server.constants import STAGE_DATABASE, STAGE_DB_SCHEMA
from api_server.readiness_pipeline import ReadinessPipelineBuilder


def add_database_connection_stage(builder: ReadinessPipelineBuilder) -> ReadinessPipelineBuilder:
    """Add database connection validation stage to pipeline (no schema checks).

    Includes:
    - Database initialization check
    - Database health check

    Args:
        builder: Pipeline builder to add stage to

    Returns:
        Builder with database connection stage added (for chaining)
    """
    (
        builder.add_stage(
            name=STAGE_DATABASE,
            description="Database connection checks",
            is_critical=False,
            fail_fast=True,
        )
        .add_check(DatabaseInitializationCheck())
        .add_check(DatabaseHealthCheck())
    )
    return builder


def build_db_basic_pipeline():
    """Build basic database pipeline with only essential checks.

    This pipeline includes only database initialization and health checks,
    which should pass even when migration is needed.

    Returns:
        Configured pipeline ready to execute
    """
    builder = ReadinessPipelineBuilder()
    add_database_connection_stage(builder)
    return builder.build()


def build_db_check_pipeline():
    """Build readiness pipeline for database check operations.

    Validates database connection, health, and schema status (no migrations).

    Returns:
        Configured pipeline ready to execute
    """
    builder = ReadinessPipelineBuilder()

    # Database connection stage
    add_database_connection_stage(builder)

    # Add schema validation check in a separate stage (no migrations)
    (
        builder.add_stage(
            name=STAGE_DB_SCHEMA,
            description="Database schema validation",
            is_critical=False,
            fail_fast=True,
        ).add_check(DatabaseSchemaCheck())
    )

    return builder.build()
