"""Enums for readiness pipeline system.

This module contains basic enums to avoid circular dependencies.
"""

from enum import StrEnum


class CheckStatus(StrEnum):
    """Status of individual checks or pipeline stages."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"
    SKIP_STAGE = "skip_stage"
    NOT_APPLICABLE = "not_applicable"


class ServerState(StrEnum):
    """Overall server health state."""

    STARTING = "starting"
    CHECKING = "checking"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"  # Some non-critical failures
    ERROR = "error"
