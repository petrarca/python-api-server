"""Tests for the service registry."""

import pytest

from api_server.services.registry import ServiceRegistry, get_service_registry


class MockService:
    """A mock service class for testing."""

    def __init__(self, value: str = "default"):
        """Initialize with a value."""
        self.value = value

    def get_value(self) -> str:
        """Get the service value."""
        return self.value


class AnotherMockService:
    """Another mock service class for testing."""

    def __init__(self, number: int = 42):
        """Initialize with a number."""
        self.number = number

    def get_number(self) -> int:
        """Get the service number."""
        return self.number


def test_register_and_get_singleton():
    """Test registering and retrieving a singleton service."""
    registry = ServiceRegistry()
    service = MockService("singleton")
    registry.register_singleton(MockService, service)
    retrieved_service = registry.get(MockService)
    assert retrieved_service is service
    assert retrieved_service.get_value() == "singleton"


def test_register_and_get_factory():
    """Test registering and retrieving a factory service."""
    registry = ServiceRegistry()
    factory_called = False

    def factory() -> MockService:
        nonlocal factory_called
        factory_called = True
        return MockService("factory")

    registry.register_factory(MockService, factory)
    retrieved_service = registry.get(MockService)
    assert factory_called
    assert retrieved_service.get_value() == "factory"

    factory_called = False
    another_service = registry.get(MockService)
    assert factory_called
    assert another_service.get_value() == "factory"
    assert another_service is not retrieved_service  # New instance each time


def test_get_unregistered_service():
    """Test getting an unregistered service raises KeyError."""
    registry = ServiceRegistry()
    with pytest.raises(KeyError, match="Service MockService not registered"):
        registry.get(MockService)


def test_multiple_services():
    """Test registering and retrieving multiple services."""
    registry = ServiceRegistry()
    service1 = MockService("first")

    def service2_factory() -> AnotherMockService:
        return AnotherMockService(100)

    registry.register_singleton(MockService, service1)
    registry.register_factory(AnotherMockService, service2_factory)

    retrieved_service1 = registry.get(MockService)
    retrieved_service2 = registry.get(AnotherMockService)

    assert retrieved_service1 is service1
    assert retrieved_service1.get_value() == "first"
    assert retrieved_service2.get_number() == 100


def test_service_registry_singleton():
    """Test that get_service_registry returns the same instance each time."""
    registry1 = get_service_registry()
    registry2 = get_service_registry()
    assert registry1 is registry2

    service = MockService("global")
    registry1.register_singleton(MockService, service)

    retrieved_service = registry2.get(MockService)
    assert retrieved_service is service
