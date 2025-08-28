"""GraphQL context with service registry integration."""

from typing import Any, TypeVar

from fastapi import Request
from sqlmodel import Session
from strawberry.fastapi import BaseContext

from api_server.services.registry import get_service_registry

T = TypeVar("T")


class GraphQLContext(BaseContext):
    """Enhanced GraphQL context with service registry access."""

    def __init__(self, db_session: Session, request: Request, **kwargs: Any):
        """Initialize the GraphQL context.

        Args:
            db_session: The database session
            request: The FastAPI request object
            **kwargs: Additional context values
        """
        super().__init__()
        self.db_session = db_session
        self.request = request
        self._registry = get_service_registry()

        # Add any additional context values
        for key, value in kwargs.items():
            setattr(self, key, value)

    def service(self, service_type: type[T]) -> T:
        """Get a service by type from the registry.

        Args:
            service_type: The type of the service to retrieve

        Returns:
            An instance of the requested service

        Raises:
            KeyError: If the requested service is not registered in the registry
        """
        try:
            return self._registry.get(service_type)
        except KeyError as e:
            # Re-raise the KeyError to ensure the error message is preserved
            raise KeyError(f"Service {service_type.__name__} not registered") from e
