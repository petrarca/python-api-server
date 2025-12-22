"""Pipeline builder for constructing readiness pipelines."""

from api_server.readiness_pipeline.base import ReadinessCheck
from api_server.readiness_pipeline.pipeline import ReadinessPipeline
from api_server.readiness_pipeline.stage import ReadinessStage


class ReadinessPipelineBuilder:
    """Builder for constructing readiness pipelines with fluent interface."""

    def __init__(self):
        """Initialize the builder."""
        self.stages: list[ReadinessStage] = []
        self._stages_by_name: dict[str, ReadinessStage] = {}

    def add_stage(
        self,
        name: str,
        description: str,
        is_critical: bool = False,
        fail_fast: bool = True,
    ) -> ReadinessStage:
        """Add a new pipeline stage and return it for chaining.

        Args:
            name: Stage name
            description: Stage description
            is_critical: If True, failure stops entire pipeline
            fail_fast: If True, stop stage on first check failure

        Returns:
            The created stage for method chaining

        Raises:
            ValueError: If stage name already exists
        """
        if name in self._stages_by_name:
            raise ValueError(f"Stage '{name}' already exists")

        stage = ReadinessStage(name, description, is_critical, fail_fast)
        self.stages.append(stage)
        self._stages_by_name[name] = stage
        return stage

    def get_stage(self, name: str) -> ReadinessStage | None:
        """Get an existing stage by name.

        Args:
            name: Stage name to lookup

        Returns:
            The stage if found, None otherwise
        """
        return self._stages_by_name.get(name)

    def add_check_to_stage(self, stage_name: str, check: ReadinessCheck) -> "ReadinessPipelineBuilder":
        """Add a check to an existing stage.

        Args:
            stage_name: Name of existing stage
            check: Check to add to the stage

        Returns:
            This builder for method chaining

        Raises:
            ValueError: If stage not found
        """
        stage = self.get_stage(stage_name)
        if not stage:
            raise ValueError(f"Stage '{stage_name}' not found")
        stage.add_check(check)
        return self

    def build(self) -> ReadinessPipeline:
        """Build the final pipeline.

        Returns:
            Configured ReadinessPipeline
        """
        return ReadinessPipeline(self.stages)

    def __str__(self) -> str:
        """String representation of the builder."""
        return f"ReadinessPipelineBuilder(stages={len(self.stages)})"


class FluentReadinessPipelineBuilder:
    """Fluent builder with method chaining for pipeline construction."""

    def __init__(self):
        """Initialize the fluent builder."""
        self.pipeline_builder = ReadinessPipelineBuilder()
        self.current_stage: ReadinessStage | None = None

    def stage(
        self,
        name: str,
        description: str,
        is_critical: bool = False,
        fail_fast: bool = True,
    ) -> "FluentReadinessPipelineBuilder":
        """Start a new pipeline stage.

        Args:
            name: Stage name
            description: Stage description
            is_critical: If True, failure stops entire pipeline
            fail_fast: If True, stop stage on first check failure

        Returns:
            This builder for method chaining
        """
        self.current_stage = self.pipeline_builder.add_stage(name, description, is_critical, fail_fast)
        return self

    def check(self, check: ReadinessCheck) -> "FluentReadinessPipelineBuilder":
        """Add a check to the current stage.

        Args:
            check: Check to add

        Returns:
            This builder for method chaining

        Raises:
            ValueError: If no current stage
        """
        if not self.current_stage:
            raise ValueError("No current stage. Call stage() first.")
        self.current_stage.add_check(check)
        return self

    def checks(self, checks: list[ReadinessCheck]) -> "FluentReadinessPipelineBuilder":
        """Add multiple checks to the current stage.

        Args:
            checks: List of checks to add

        Returns:
            This builder for method chaining

        Raises:
            ValueError: If no current stage
        """
        if not self.current_stage:
            raise ValueError("No current stage. Call stage() first.")
        self.current_stage.add_checks(checks)
        return self

    def build(self) -> ReadinessPipeline:
        """Build the final pipeline.

        Returns:
            Configured ReadinessPipeline
        """
        return self.pipeline_builder.build()

    def __str__(self) -> str:
        """String representation of the fluent builder."""
        stages = len(self.pipeline_builder.stages)
        current = self.current_stage.name if self.current_stage else "None"
        return f"FluentReadinessPipelineBuilder(stages={stages}, current={current})"
