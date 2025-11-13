"""Tests for self-check pipeline stages."""

from api_server.readiness_pipeline import CheckStatus, ReadinessCheck, ReadinessCheckResult, ReadinessStage


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


class TestReadinessStage:
    """Test ReadinessStage class."""

    def test_stage_initialization(self):
        """Test stage initialization."""
        stage = ReadinessStage(
            "test_stage",
            "Test stage description",
            is_critical=True,
            fail_fast=False,
            run_once=True,
        )

        assert stage.name == "test_stage"
        assert stage.description == "Test stage description"
        assert stage.is_critical is True
        assert stage.fail_fast is False
        assert stage.run_once is True
        assert stage.checks == []

    def test_add_single_check(self):
        """Test adding a single check to stage."""
        stage = ReadinessStage("test_stage", "Test stage")
        check = MockReadinessCheck("test_check")

        result = stage.add_check(check)

        assert result is stage  # Fluent interface
        assert len(stage.checks) == 1
        assert stage.checks[0] is check

    def test_add_multiple_checks(self):
        """Test adding multiple checks to stage."""
        stage = ReadinessStage("test_stage", "Test stage")
        check1 = MockReadinessCheck("check1")
        check2 = MockReadinessCheck("check2")

        result = stage.add_checks([check1, check2])

        assert result is stage  # Fluent interface
        assert len(stage.checks) == 2
        assert check1 in stage.checks
        assert check2 in stage.checks

    def test_successful_stage_execution(self):
        """Test successful stage execution."""
        check1 = MockReadinessCheck("check1")
        check2 = MockReadinessCheck("check2")
        stage = ReadinessStage("test_stage", "Test stage").add_checks([check1, check2])

        result = stage.execute()

        assert result.stage_name == "test_stage"
        assert result.status == CheckStatus.SUCCESS
        assert result.total_checks == 2
        assert result.successful_checks == 2
        assert result.failed_checks == 0
        assert result.skipped_checks == 0
        assert len(result.check_results) == 2

        # Verify all checks were executed
        assert check1.execute_called
        assert check2.execute_called

        # Verify check results have stage name
        for check_result in result.check_results:
            assert check_result.stage_name == "test_stage"

    def test_stage_with_failures(self):
        """Test stage execution with failures."""
        check1 = MockReadinessCheck("check1")  # Success
        check2 = MockReadinessCheck("check2", should_fail=True)  # Failure
        stage = ReadinessStage("test_stage", "Test stage", fail_fast=False).add_checks([check1, check2])

        result = stage.execute()

        assert result.status == CheckStatus.FAILED
        assert result.successful_checks == 1
        assert result.failed_checks == 1
        assert result.skipped_checks == 0

    def test_stage_fail_fast(self):
        """Test stage fail-fast behavior."""
        check1 = MockReadinessCheck("check1", should_fail=True)  # Failure
        check2 = MockReadinessCheck("check2")  # Should be skipped
        stage = ReadinessStage("test_stage", "Test stage", fail_fast=True).add_checks([check1, check2])

        result = stage.execute()

        assert result.status == CheckStatus.FAILED
        assert result.failed_checks == 1
        assert result.skipped_checks == 1
        assert len(result.check_results) == 2

        # First check executed, second skipped
        assert check1.execute_called
        assert not check2.execute_called

    def test_critical_check_failure(self):
        """Test critical check failure behavior."""
        check1 = MockReadinessCheck("check1", is_critical=True, should_fail=True)
        check2 = MockReadinessCheck("check2")  # Should be skipped
        stage = ReadinessStage("test_stage", "Test stage", fail_fast=False).add_checks([check1, check2])

        result = stage.execute()

        assert result.status == CheckStatus.FAILED
        assert result.failed_checks == 1
        assert result.skipped_checks == 1

        # First check executed, second skipped due to critical failure
        assert check1.execute_called
        assert not check2.execute_called

    def test_stage_run_once_behavior(self):
        """Test stage run_once functionality."""
        check = MockReadinessCheck("test_check")
        stage = ReadinessStage("test_stage", "Test stage", run_once=True)
        stage.add_check(check)

        # First execution
        result1 = stage.execute()
        assert result1.status == CheckStatus.SUCCESS
        assert check.execute_called

        # Reset check state to verify caching
        check.execute_called = False

        # Second execution should return cached result
        result2 = stage.execute()
        assert result2 is result1  # Same object
        assert not check.execute_called  # Check not executed again

    def test_stage_reset_functionality(self):
        """Test stage reset functionality."""
        check = MockReadinessCheck("test_check", run_once=True)
        stage = ReadinessStage("test_stage", "Test stage", run_once=True)
        stage.add_check(check)

        # Execute once
        result1 = stage.execute()
        assert check.execute_called

        # Reset stage (should reset both stage and checks)
        stage.reset()

        # Execute again should create new result
        check.execute_called = False
        result2 = stage.execute()
        assert result2 is not result1  # Different object
        assert check.execute_called

    def test_skip_stage_status(self):
        """Test SKIP_STAGE status handling."""

        # Create a check that returns SKIP_STAGE
        class SkipStageCheck(ReadinessCheck):
            def _execute(self):
                return self.skip_stage("Stage should be skipped")

        check1 = SkipStageCheck("skip_check")
        check2 = MockReadinessCheck("normal_check")  # Should be skipped
        stage = ReadinessStage("test_stage", "Test stage").add_checks([check1, check2])

        result = stage.execute()

        assert result.status == CheckStatus.SKIPPED
        assert result.skipped_checks == 2  # Both checks marked as skipped
        assert len(result.check_results) == 2

    def test_not_applicable_status(self):
        """Test NOT_APPLICABLE status handling."""

        # Create a check that returns NOT_APPLICABLE
        class NotApplicableCheck(ReadinessCheck):
            def _execute(self):
                return self.not_applicable("Check not applicable")

        check1 = NotApplicableCheck("na_check")
        check2 = MockReadinessCheck("normal_check")
        stage = ReadinessStage("test_stage", "Test stage").add_checks([check1, check2])

        result = stage.execute()

        assert result.status == CheckStatus.SUCCESS
        assert result.successful_checks == 1  # Only normal_check
        assert result.skipped_checks == 1  # NOT_APPLICABLE check
        assert result.failed_checks == 0

    def test_stage_string_representation(self):
        """Test stage string representations."""
        stage = ReadinessStage("test_stage", "Test description")
        stage.add_check(MockReadinessCheck("check1"))
        stage.add_check(MockReadinessCheck("check2"))

        str_repr = str(stage)
        assert "test_stage" in str_repr
        assert "2" in str_repr  # Check count

        detailed_repr = repr(stage)
        assert "test_stage" in detailed_repr
        assert "Test description" in detailed_repr

    def test_run_once_field_in_stage_results(self):
        """Test that run_once field is properly set in stage results."""
        # Test with run_once=True
        check = MockReadinessCheck("test_check")
        stage_with_run_once = ReadinessStage("test_stage", "Test stage", run_once=True)
        stage_with_run_once.add_check(check)

        result = stage_with_run_once.execute()
        assert result.run_once is True

        # Test with run_once=False (default)
        stage_without_run_once = ReadinessStage("test_stage", "Test stage", run_once=False)
        stage_without_run_once.add_check(MockReadinessCheck("test_check"))

        result = stage_without_run_once.execute()
        assert result.run_once is False
