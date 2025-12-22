"""Tests for self-check pipeline."""

from unittest.mock import Mock, patch

from api_server.readiness_pipeline import (
    CheckStatus,
    ReadinessCheck,
    ReadinessCheckResult,
    ReadinessPipeline,
    ReadinessPipelineResult,
    ReadinessStage,
    ServerState,
)


class MockReadinessCheck(ReadinessCheck):
    """Mock self check for testing."""

    def __init__(
        self,
        name: str,
        is_critical: bool = False,
        run_once: bool = False,
        should_fail: bool = False,
    ):
        super().__init__(name, is_critical, run_once)
        self.should_fail = should_fail
        self.execute_called = False

    def _execute(self) -> ReadinessCheckResult:
        """Mock execute method."""
        self.execute_called = True
        if self.should_fail:
            return self.failed(f"{self.name} failed", {"error": "mock error"})
        return self.success(f"{self.name} passed", {"data": "mock data"})


class TestReadinessPipelineResult:
    """Test ReadinessPipelineResult model."""

    def test_create_pipeline_result(self):
        """Test creating a pipeline result."""
        stage_result = ReadinessStage("test_stage", "Test stage").execute()

        result = ReadinessPipelineResult(
            server_state=ServerState.OPERATIONAL,
            overall_status=CheckStatus.SUCCESS,
            message="Pipeline completed successfully",
            stage_results=[stage_result],
            total_execution_time_ms=100.0,
        )

        assert result.server_state == ServerState.OPERATIONAL
        assert result.overall_status == CheckStatus.SUCCESS
        assert result.message == "Pipeline completed successfully"
        assert len(result.stage_results) == 1
        assert result.total_execution_time_ms == 100.0

        # Test summary statistics
        assert result.total_stages == 0  # Default value
        assert result.successful_stages == 0
        assert result.failed_stages == 0
        assert result.skipped_stages == 0


class TestReadinessPipeline:
    """Test ReadinessPipeline class."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        stage1 = ReadinessStage("stage1", "Stage 1")
        stage2 = ReadinessStage("stage2", "Stage 2")
        pipeline = ReadinessPipeline([stage1, stage2])

        assert len(pipeline.stages) == 2
        assert pipeline.current_state == ServerState.STARTING
        assert pipeline.get_current_state() == ServerState.STARTING
        assert pipeline.get_last_result() is None

    def test_empty_pipeline(self):
        """Test pipeline with no stages."""
        pipeline = ReadinessPipeline([])
        result = pipeline.execute()

        assert result.server_state == ServerState.OPERATIONAL
        assert result.overall_status == CheckStatus.SUCCESS
        assert result.total_stages == 0
        assert result.total_checks == 0

    def test_successful_pipeline(self):
        """Test pipeline with all successful stages."""
        check1 = MockReadinessCheck("check1")
        check2 = MockReadinessCheck("check2")

        stage1 = ReadinessStage("stage1", "Stage 1").add_check(check1)
        stage2 = ReadinessStage("stage2", "Stage 2").add_check(check2)

        pipeline = ReadinessPipeline([stage1, stage2])
        result = pipeline.execute()

        assert result.server_state == ServerState.OPERATIONAL
        assert result.overall_status == CheckStatus.SUCCESS
        assert result.total_stages == 2
        assert result.successful_stages == 2
        assert result.failed_stages == 0
        assert result.total_checks == 2
        assert result.successful_checks == 2
        assert result.failed_checks == 0

        # Verify all checks were executed
        assert check1.execute_called
        assert check2.execute_called

        # Verify pipeline state updated
        assert pipeline.get_current_state() == ServerState.OPERATIONAL
        assert pipeline.get_last_result() == result

    def test_pipeline_with_failure(self):
        """Test pipeline with stage failures."""
        success_check = MockReadinessCheck("success_check")
        failure_check = MockReadinessCheck("failure_check", should_fail=True)

        stage1 = ReadinessStage("stage1", "Stage 1").add_check(success_check)
        stage2 = ReadinessStage("stage2", "Stage 2").add_check(failure_check)

        pipeline = ReadinessPipeline([stage1, stage2])
        result = pipeline.execute()

        assert result.server_state == ServerState.DEGRADED
        assert result.overall_status == CheckStatus.FAILED
        assert result.successful_stages == 1
        assert result.failed_stages == 1
        assert result.successful_checks == 1
        assert result.failed_checks == 1

    def test_critical_stage_failure(self):
        """Test pipeline with critical stage failure."""
        success_check = MockReadinessCheck("success_check")
        failure_check = MockReadinessCheck("failure_check", should_fail=True)
        never_run_check = MockReadinessCheck("never_run_check")

        stage1 = ReadinessStage("stage1", "Stage 1").add_check(success_check)
        stage2 = ReadinessStage("stage2", "Stage 2", is_critical=True).add_check(failure_check)
        stage3 = ReadinessStage("stage3", "Stage 3").add_check(never_run_check)

        pipeline = ReadinessPipeline([stage1, stage2, stage3])
        result = pipeline.execute()

        assert result.server_state == ServerState.ERROR
        assert result.overall_status == CheckStatus.FAILED
        assert result.successful_stages == 1
        assert result.failed_stages == 1
        assert result.skipped_stages == 1  # Stage 3 skipped

        # Only first two checks should have been executed
        assert success_check.execute_called
        assert failure_check.execute_called
        assert not never_run_check.execute_called

    def test_pipeline_reset_functionality(self):
        """Test pipeline reset functionality."""
        check = MockReadinessCheck("test_check", run_once=True)
        stage = ReadinessStage("test_stage", "Test stage", run_once=True)
        stage.add_check(check)

        pipeline = ReadinessPipeline([stage])

        # Execute once
        result1 = pipeline.execute()
        assert pipeline.get_current_state() == ServerState.OPERATIONAL
        assert pipeline.get_last_result() is result1

        # Reset pipeline
        pipeline.reset()
        assert pipeline.get_current_state() == ServerState.STARTING
        assert pipeline.get_last_result() is None

        # Execute again should create new result
        result2 = pipeline.execute()
        assert result2 is not result1  # Different object

    @patch("api_server.readiness_pipeline.calculator.arrow.utcnow")
    def test_pipeline_execution_timing(self, mock_calc_arrow):
        """Test that pipeline execution timing is recorded."""
        # Use a simple incrementing function for time with enough values
        time_values = iter([0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09])

        def mock_arrow():
            timestamp = next(time_values)
            return Mock(float_timestamp=timestamp, isoformat=lambda: f"2023-01-01T00:00:{timestamp:.2f}Z")

        check = MockReadinessCheck("check1")
        stage = ReadinessStage("stage1", "Stage 1").add_check(check)
        pipeline = ReadinessPipeline([stage])

        # Patch all arrow.utcnow() calls to use the same iterator
        with (
            patch("api_server.readiness_pipeline.executor.arrow.utcnow", side_effect=mock_arrow),
            patch("api_server.readiness_pipeline.stage.arrow.utcnow", side_effect=mock_arrow),
            patch("api_server.readiness_pipeline.check_executor.arrow.utcnow", side_effect=mock_arrow),
        ):
            mock_calc_arrow.return_value = Mock(float_timestamp=0.06, isoformat=lambda: "2023-01-01T00:00:00Z")
            result = pipeline.execute()

        assert result.total_execution_time_ms is not None
        assert result.total_execution_time_ms > 0

    def test_pipeline_string_representation(self):
        """Test pipeline string representations."""
        stage1 = ReadinessStage("stage1", "Stage 1")
        stage2 = ReadinessStage("stage2", "Stage 2")
        pipeline = ReadinessPipeline([stage1, stage2])

        str_repr = str(pipeline)
        assert "2" in str_repr  # Stage count

        detailed_repr = repr(pipeline)
        assert "stage1" in detailed_repr
        assert "stage2" in detailed_repr
