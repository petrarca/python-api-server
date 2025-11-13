"""Reusable pipeline stage builders.

This module provides functions to build common pipeline stages that can be
reused by both the server startup pipeline and CLI pipelines.
"""

from api_server.readiness_pipeline import ReadinessPipelineBuilder

from .alembic_setup import AlembicSetupCheck
from .database_health_check import DatabaseHealthCheck
from .database_initialization import DatabaseInitializationCheck
from .database_version import DatabaseVersionCheck


def add_database_stage(builder: ReadinessPipelineBuilder) -> ReadinessPipelineBuilder:
    """Add database validation stage to pipeline.

    Includes:
    - Database initialization check
    - Database health check
    - Alembic setup check
    - Database version check

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
        .add_check(AlembicSetupCheck())
        .add_check(DatabaseVersionCheck())
    )
    return builder
