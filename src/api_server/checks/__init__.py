"""Readiness check registry and factory functions for pipeline."""

from functools import lru_cache

from api_server.readiness_pipeline import ReadinessPipeline, ReadinessPipelineBuilder

# Import pipeline builders
from .pipeline_builders import add_database_stage


def _create_readiness_pipeline() -> ReadinessPipeline:
    """Get the default readiness pipeline for server startup.

    Creates a pipeline with stages:
    1. Database stage (non-critical) - metadata DB, alembic setup, DB version

    Returns:
        ReadinessPipeline: The readiness pipeline for this server
    """
    builder = ReadinessPipelineBuilder()

    # Add stages using reusable builders
    add_database_stage(builder)

    return builder.build()


@lru_cache(maxsize=1)
def get_readiness_pipeline() -> ReadinessPipeline:
    """Get the singleton readiness pipeline instance.

    This function should be used by services that need the configured pipeline.
    It creates a single instance and caches it for the lifetime of the process.

    Returns:
        ReadinessPipeline: The singleton readiness pipeline instance
    """
    return _create_readiness_pipeline()


__all__ = [
    "get_readiness_pipeline",
]
