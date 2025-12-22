"""Tests for CheckExecutor class."""

from unittest.mock import Mock, patch

from api_server.readiness_pipeline.base import CheckStatus, ReadinessCheck, ReadinessCheckResult
from api_server.readiness_pipeline.check_executor import CheckExecutor


class MockReadinessCheck(ReadinessCheck):
    """Mock readiness check for testing."""

    def __init__(self, name: str, should_fail: bool = False, should_raise: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.should_raise = should_raise
        self.execute_called = False
        self.force_rerun_called = False

    def _execute(self) -> ReadinessCheckResult:
        """Mock execute method."""
        self.execute_called = True

        if self.should_raise:
            raise ValueError(f"Mock check {self.name} failed")

        if self.should_fail:
            return ReadinessCheckResult(
                status=CheckStatus.FAILED,
                message=f"Check {self.name} failed",
                check_name=self.name,
            )
        else:
            return ReadinessCheckResult(
                status=CheckStatus.SUCCESS,
                message=f"Check {self.name} passed",
                check_name=self.name,
            )


class TestCheckExecutor:
    """Test cases for CheckExecutor."""

    def test_execute_successful_check(self):
        """Test executing a successful check."""
        executor = CheckExecutor()
        check = MockReadinessCheck("test_check", should_fail=False)

        result = executor.execute_single_check(check, "test_stage")

        assert result.status == CheckStatus.SUCCESS
        assert result.check_name == "test_check"
        assert result.stage_name == "test_stage"
        assert result.message == "Check test_check passed"
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0
        assert result.executed_at is not None
        assert check.execute_called is True

    def test_execute_failing_check(self):
        """Test executing a failing check."""
        executor = CheckExecutor()
        check = MockReadinessCheck("failing_check", should_fail=True)

        result = executor.execute_single_check(check, "test_stage")

        assert result.status == CheckStatus.FAILED
        assert result.check_name == "failing_check"
        assert result.stage_name == "test_stage"
        assert result.message == "Check failing_check failed"
        assert result.execution_time_ms is not None
        assert result.executed_at is not None
        assert check.execute_called is True

    def test_execute_check_with_exception(self):
        """Test executing a check that raises an exception."""
        executor = CheckExecutor()
        check = MockReadinessCheck("error_check", should_raise=True)

        result = executor.execute_single_check(check, "test_stage")

        assert result.status == CheckStatus.FAILED
        assert result.check_name == "error_check"
        assert result.stage_name == "test_stage"
        assert "Check execution failed" in result.message
        assert "Mock check error_check failed" in result.message
        assert result.execution_time_ms is not None
        assert result.executed_at is not None
        assert result.details is not None
        assert result.details["exception"] == "Mock check error_check failed"
        assert result.details["type"] == "ValueError"
        assert check.execute_called is True

    @patch("api_server.readiness_pipeline.check_executor.arrow.utcnow")
    def test_execute_check_timing(self, mock_arrow):
        """Test that check execution timing is recorded correctly."""
        executor = CheckExecutor()
        check = MockReadinessCheck("timing_check")

        # Mock timing: start at 0.0, end at 0.1 (100ms) - need 3 calls for timing
        mock_arrow.side_effect = [
            Mock(float_timestamp=0.0, isoformat=lambda: "2023-01-01T00:00:00Z"),  # start time
            Mock(float_timestamp=0.1, isoformat=lambda: "2023-01-01T00:00:00Z"),  # end time
            Mock(float_timestamp=0.1, isoformat=lambda: "2023-01-01T00:00:00Z"),  # timestamp for result
        ]

        result = executor.execute_single_check(check, "test_stage")

        assert result.execution_time_ms == 100.0  # (0.1 - 0.0) * 1000

    @patch("api_server.readiness_pipeline.check_executor.arrow.utcnow")
    def test_execute_check_timestamp(self, mock_utcnow):
        """Test that check execution timestamp is recorded correctly."""
        executor = CheckExecutor()
        check = MockReadinessCheck("timestamp_check")

        mock_iso = "2023-01-01T12:00:00.000Z"
        mock_utcnow.return_value.isoformat.return_value = mock_iso

        result = executor.execute_single_check(check, "test_stage")

        assert result.executed_at == mock_iso

    def test_force_rerun_parameter(self):
        """Test that force_rerun parameter is passed to check."""
        executor = CheckExecutor()
        check = MockReadinessCheck("rerun_check")

        # The CheckExecutor doesn't directly expose force_rerun to the check
        # since ReadinessCheck handles that internally via its run() method
        # We just verify the check executes successfully
        result = executor.execute_single_check(check, "test_stage", force_rerun=True)
        assert result.status == CheckStatus.SUCCESS
        assert check.execute_called is True

    def test_stage_name_traceability(self):
        """Test that stage name is properly added to result for traceability."""
        executor = CheckExecutor()
        check = MockReadinessCheck("traceability_check")

        result = executor.execute_single_check(check, "my_test_stage")

        assert result.stage_name == "my_test_stage"

    def test_exception_in_timing_calculation(self):
        """Test handling of exceptions during timing calculation."""
        executor = CheckExecutor()
        check = MockReadinessCheck("timing_error_check", should_raise=True)

        # Even if the check raises an exception, timing should still be calculated
        with patch("api_server.readiness_pipeline.check_executor.arrow.utcnow") as mock_arrow:
            mock_arrow.side_effect = [
                Mock(float_timestamp=0.0, isoformat=lambda: "2023-01-01T00:00:00Z"),  # start time
                Mock(float_timestamp=0.05, isoformat=lambda: "2023-01-01T00:00:00Z"),  # end time
                Mock(float_timestamp=0.05, isoformat=lambda: "2023-01-01T00:00:00Z"),  # timestamp for executed_at
                Mock(float_timestamp=0.05, isoformat=lambda: "2023-01-01T00:00:00Z"),  # timestamp for execution_time_ms
            ]  # 50ms execution time

            result = executor.execute_single_check(check, "test_stage")

            assert result.status == CheckStatus.FAILED
            assert result.execution_time_ms == 50.0
