"""Data models for readiness pipeline system.

This module contains Pydantic models used throughout the readiness pipeline
to avoid circular dependencies between components.
"""

from typing import Any

import arrow
from pydantic import BaseModel, Field

from .enums import CheckStatus, ServerState


class ReadinessCheckResult(BaseModel):
    """Result of an individual readiness check."""

    model_config = {"use_enum_values": True}

    status: CheckStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    check_name: str
    stage_name: str | None = None
    executed_at: str | None = None  # ISO 8601 UTC timestamp
    execution_time_ms: float | None = None
    run_once: bool = False


class ReadinessStageResult(BaseModel):
    """Result of a readiness pipeline stage (group of related checks)."""

    model_config = {"use_enum_values": True}

    stage_name: str
    status: CheckStatus
    message: str
    check_results: list[ReadinessCheckResult] = Field(default_factory=list)
    executed_at: str | None = None  # ISO 8601 UTC timestamp
    execution_time_ms: float | None = None
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    skipped_checks: int = 0
    run_once: bool = False


class ReadinessPipelineResult(BaseModel):
    """Complete result of a readiness pipeline execution."""

    model_config = {"use_enum_values": True}

    overall_status: CheckStatus
    server_state: ServerState
    message: str
    stage_results: list[ReadinessStageResult] = Field(default_factory=list)
    check_results: list[ReadinessCheckResult] = Field(default_factory=list)
    executed_at: str = Field(default_factory=lambda: arrow.utcnow().isoformat())
    execution_time_ms: float | None = None
    total_execution_time_ms: float | None = None
    total_stages: int = 0
    successful_stages: int = 0
    failed_stages: int = 0
    skipped_stages: int = 0
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    skipped_checks: int = 0
