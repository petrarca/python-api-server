"""Tests for the GraphQL context class."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from sqlmodel import Session

# Create a mock database module to avoid database connection requirements
mock_db = MagicMock()
sys.modules["api_server.database"] = mock_db

# Import after mocking the database
from api_server.graphql.context import GraphQLContext  # noqa: E402
from api_server.services.registry import ServiceRegistry  # noqa: E402


class MockService:
    """A mock service class for testing."""

    def __init__(self, value: str = "default"):
        """Initialize with a value."""
        self.value = value

    def get_value(self) -> str:
        """Get the service value."""
        return self.value


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_request():
    """Create a mock request."""
    return Request({"type": "http"})


@pytest.fixture
def test_registry():
    """Create a test registry."""
    return ServiceRegistry()


@pytest.fixture
def patch_registry(test_registry):
    """Patch the get_service_registry function to return our test registry."""
    with patch("api_server.graphql.context.get_service_registry", return_value=test_registry):
        yield test_registry


def test_graphql_context_service_access(mock_request, mock_db_session, patch_registry):
    """Test that the GraphQL context can access services from the registry."""
    # Register a test service in our patched registry
    test_service = MockService("test_value")
    patch_registry.register_singleton(MockService, test_service)
    # Create a context that will use our patched registry
    context = GraphQLContext(db_session=mock_db_session, request=mock_request)
    # Get the service from the context
    retrieved_service = context.service(MockService)
    # Verify it's the same service we registered
    assert retrieved_service is test_service
    assert retrieved_service.get_value() == "test_value"


def test_graphql_context_additional_values(mock_request, mock_db_session):
    """Test that the GraphQL context can store additional values."""
    context = GraphQLContext(db_session=mock_db_session, request=mock_request, custom_value="custom", another_value=42)
    assert context.custom_value == "custom"
    assert context.another_value == 42
    assert context.db_session is mock_db_session
    assert context.request is mock_request


def test_graphql_context_service_not_found(mock_request, mock_db_session, patch_registry):  # noqa: ARG001
    """Test that the GraphQL context raises an error for unregistered services."""
    # We need the patch_registry fixture to ensure we have a clean registry for this test,
    # even though we don't directly use the fixture in the test body
    # Create a context with an empty registry
    context = GraphQLContext(db_session=mock_db_session, request=mock_request)
    # Try to get a service that doesn't exist
    with pytest.raises(KeyError, match="Service MockService not registered"):
        context.service(MockService)
