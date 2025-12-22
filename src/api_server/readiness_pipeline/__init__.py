"""Server readiness pipeline module with pipeline architecture.

This module provides a readiness verification system with pipeline architecture:
- Pipeline stages group related checks
- Sequential execution with proper failure handling
- Critical stages and checks control execution flow
- Rich reporting with hierarchical results

The pipeline runtime is decoupled from specific check implementations.
Check implementations and pipeline configuration are in the checks submodule.
"""

# Import pipeline infrastructure components
# Import core models
from .base import ReadinessCheck
from .builder import FluentReadinessPipelineBuilder, ReadinessPipelineBuilder
from .enums import CheckStatus, ServerState
from .models import ReadinessCheckResult, ReadinessPipelineResult, ReadinessStageResult
from .pipeline import ReadinessPipeline
from .stage import ReadinessStage

# Public API - Only infrastructure components, no specific check implementations
__all__ = [
    # Core models
    "CheckStatus",
    "ReadinessStageResult",
    "ReadinessCheck",
    "ReadinessPipelineResult",
    "ReadinessCheckResult",
    "ServerState",
    # Pipeline components
    "ReadinessStage",
    "ReadinessPipeline",
    "ReadinessPipelineBuilder",
    "FluentReadinessPipelineBuilder",
]
