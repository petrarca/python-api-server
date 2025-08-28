"""API dependencies for FastAPI endpoints."""

from collections.abc import Callable
from typing import TypeVar

from api_server.services.registry import get_service_registry

T = TypeVar("T")


def service[T](service_type: type[T]) -> Callable[[], T]:
    """FastAPI dependency that provides a service by type.

    Args:
        service_type: The type of service to retrieve from the registry

    Returns:
        A callable that returns the requested service instance

    Example:
        ```python
        @router.get("/endpoint")
        def endpoint(service: MyService = Depends(service(MyService))):
            return service.do_something()
        ```
    """

    def get_service() -> T:
        registry = get_service_registry()
        return registry.get(service_type)

    return get_service
