"""Service registry for dependency injection."""

from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar, cast

T = TypeVar("T")
ServiceFactory = Callable[[], T]
ServiceProvider = T | ServiceFactory[T]


class ServiceRegistry:
    """Registry for all shared services with support for singletons and factories."""

    def __init__(self):
        """Initialize an empty service registry."""
        self._services: dict[str, ServiceProvider[Any]] = {}

    def register_singleton(self, service_type: type[T], instance: T) -> None:
        """Register a singleton instance by its type.

        Args:
            service_type: The type of the service to register
            instance: The singleton instance to register
        """
        self._services[service_type.__name__] = instance

    def register_factory(self, service_type: type[T], factory: ServiceFactory[T]) -> None:
        """Register a factory function by its type.

        Args:
            service_type: The type of the service to register
            factory: The factory function that creates instances of the service
        """
        self._services[service_type.__name__] = factory

    def get(self, service_type: type[T]) -> T:
        """Get a service instance by type.

        Args:
            service_type: The type of the service to retrieve

        Returns:
            An instance of the requested service

        Raises:
            KeyError: If the requested service is not registered
        """
        service_name = service_type.__name__

        if service_name not in self._services:
            raise KeyError(f"Service {service_name} not registered")

        provider = self._services[service_name]

        # If provider is a factory function, call it to get an instance
        if callable(provider) and not isinstance(provider, type):
            return provider()

        # Otherwise, it's already an instance
        return cast(T, provider)


@lru_cache
def get_service_registry() -> ServiceRegistry:
    """Get the singleton service registry instance.

    Returns:
        The global service registry instance
    """
    return ServiceRegistry()
