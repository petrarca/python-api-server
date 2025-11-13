"""Tests for self-check models and base classes."""

from api_server.readiness_pipeline import CheckStatus, ReadinessCheck, ReadinessCheckResult


class MockReadinessCheck(ReadinessCheck):
    """Mock self check for testing."""

    def __init__(self, name: str, is_critical: bool = False, run_once: bool = False, should_fail: bool = False):
        super().__init__(name, is_critical, run_once)
        self.should_fail = should_fail
        self.execute_called = False

    def _execute(self) -> ReadinessCheckResult:
        """Mock execute method."""
        self.execute_called = True
        if self.should_fail:
            return self.failed(f"{self.name} failed", {"error": "mock error"})
        return self.success(f"{self.name} passed", {"data": "mock data"})


class TestReadinessCheckResult:
    """Test ReadinessCheckResult model."""

    def test_create_result(self):
        """Test creating a self check result."""
        result = ReadinessCheckResult(
            status=CheckStatus.SUCCESS,
            message="Test passed",
            check_name="test_check",
            details={"key": "value"},
        )

        assert result.status == CheckStatus.SUCCESS
        assert result.message == "Test passed"
        assert result.check_name == "test_check"
        assert result.details == {"key": "value"}
        assert result.execution_time_ms is None

    def test_result_with_stage_name(self):
        """Test creating a result with stage name."""
        result = ReadinessCheckResult(
            status=CheckStatus.SUCCESS,
            message="Test passed",
            check_name="test_check",
            stage_name="test_stage",
        )

        assert result.stage_name == "test_stage"


class TestReadinessCheck:
    """Test ReadinessCheck base class."""

    def test_basic_initialization(self):
        """Test basic self check initialization."""
        check = MockReadinessCheck("test_check", is_critical=True, run_once=False)

        assert check.name == "test_check"
        assert check.is_critical is True
        assert check.run_once is False
        assert check._executed_once is False
        assert check._last_result is None

    def test_run_once_initialization(self):
        """Test self check with run_once enabled."""
        check = MockReadinessCheck("test_check", run_once=True)

        assert check.run_once is True
        assert check._executed_once is False
        assert check._last_result is None

    def test_successful_execution(self):
        """Test successful check execution."""
        check = MockReadinessCheck("test_check")
        result = check.run()

        assert result.status == CheckStatus.SUCCESS
        assert result.message == "test_check passed"
        assert result.check_name == "test_check"
        assert result.details == {"data": "mock data"}
        assert check.execute_called is True

    def test_failed_execution(self):
        """Test failed check execution."""
        check = MockReadinessCheck("test_check", should_fail=True)
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert result.message == "test_check failed"
        assert result.details == {"error": "mock error"}

    def test_run_once_behavior(self):
        """Test run_once functionality."""
        check = MockReadinessCheck("test_check", run_once=True)

        # First execution
        result1 = check.run()
        assert result1.status == CheckStatus.SUCCESS
        assert check.execute_called is True
        assert check._executed_once is True
        assert check._last_result is result1

        # Reset the execute_called flag to test caching
        check.execute_called = False

        # Second execution should return cached result
        result2 = check.run()
        assert result2 is result1  # Same object
        assert check.execute_called is False  # _execute was not called again

    def test_reset_functionality(self):
        """Test reset functionality."""
        check = MockReadinessCheck("test_check", run_once=True)

        # Execute once
        result1 = check.run()
        assert check._executed_once is True
        assert check._last_result is result1

        # Reset
        check.reset()
        assert check._executed_once is False
        assert check._last_result is None

        # Execute again should create new result
        check.execute_called = False
        result2 = check.run()
        assert result2 is not result1  # Different object
        assert check.execute_called is True

    def test_helper_methods(self):
        """Test helper methods for creating results."""
        check = MockReadinessCheck("test_check")

        # Test success helper
        result = check.success("Success message", {"key": "value"})
        assert result.status == CheckStatus.SUCCESS
        assert result.message == "Success message"
        assert result.check_name == "test_check"
        assert result.details == {"key": "value"}

        # Test failed helper
        result = check.failed("Failed message", {"error": "test"})
        assert result.status == CheckStatus.FAILED
        assert result.message == "Failed message"
        assert result.details == {"error": "test"}

        # Test warning helper
        result = check.warning("Warning message")
        assert result.status == CheckStatus.WARNING
        assert result.message == "Warning message"
        assert result.details == {}

        # Test not_applicable helper
        result = check.not_applicable("Not applicable message")
        assert result.status == CheckStatus.NOT_APPLICABLE
        assert result.message == "Not applicable message"

        # Test skip_stage helper
        result = check.skip_stage("Skip stage message")
        assert result.status == CheckStatus.SKIP_STAGE
        assert result.message == "Skip stage message"

    def test_run_once_field_in_results(self):
        """Test that run_once field is properly set in results."""
        # Test with run_once=True
        check_with_run_once = MockReadinessCheck("test_check", run_once=True)
        result = check_with_run_once.success("Success message")
        assert result.run_once is True

        # Test with run_once=False (default)
        check_without_run_once = MockReadinessCheck("test_check", run_once=False)
        result = check_without_run_once.success("Success message")
        assert result.run_once is False

        # Test all helper methods include run_once field correctly
        check = MockReadinessCheck("test_check", run_once=True)

        result = check.failed("Failed message")
        assert result.run_once is True

        result = check.warning("Warning message")
        assert result.run_once is True

        result = check.not_applicable("Not applicable message")
        assert result.run_once is True

        result = check.skip_stage("Skip stage message")
        assert result.run_once is True
