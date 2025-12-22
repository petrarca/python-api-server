"""Reusable pipeline stage builders for API server template.

This module provides functions to build common pipeline stages that can be
reused across different applications.
"""

from api_server.readiness_pipeline import ReadinessPipelineBuilder

# Import essential checks only
from .database_health_check import DatabaseHealthCheck
from .database_initialization import DatabaseInitializationCheck
from .database_schema_check import DatabaseSchemaCheck


def add_database_stage(builder: ReadinessPipelineBuilder) -> ReadinessPipelineBuilder:
    """Add database validation stage to pipeline.

    Includes:
    - Database initialization check
    - Database health check
    - Database schema check (validates schema state, no auto-migration)

    Args:
        builder: Pipeline builder to add stage to

    Returns:
        Builder with database stage added (for chaining)
    """
    (
        builder.add_stage(
            name="database",
            description="Database checks",
            is_critical=False,
            fail_fast=True,
        )
        .add_check(DatabaseInitializationCheck())
        .add_check(DatabaseHealthCheck())
        .add_check(DatabaseSchemaCheck())
    )
    return builder
