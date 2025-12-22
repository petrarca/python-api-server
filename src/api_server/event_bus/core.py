"""Core Event Bus Components.

This module contains the fundamental abstractions for the event bus system.
These components are framework-agnostic and can be used in any async Python
application.

## Key Components

- **EventHandler**: Base class for dependency-injectable event handlers
- **EventBusError**: Base exception for all event bus related errors
- **HandlerRegistrationError**: Raised when handler registration fails
- **EventEmissionError**: Raised when event emission fails

## Usage Example with Dependency Injection

```python
from api_server.event_bus.core import EventHandler
from pydantic import BaseModel

class OrderCreatedEvent(BaseModel):
    order_id: str
    customer_id: str

class OrderProcessor(EventHandler[OrderCreatedEvent]):
    def __init__(self, email_service: EmailService, inventory_service: InventoryService):
        self.email_service = email_service
        self.inventory_service = inventory_service

    async def handle(self, event: OrderCreatedEvent) -> str:
        # Process order using injected dependencies
        await self.inventory_service.reserve_items(event.order_id)
        await self.email_service.send_confirmation(event.customer_id)
        return f"Order {event.order_id} processed"

# The EventBus will automatically inject EmailService and InventoryService
# when the handler is instantiated, provided they are registered in the ServiceRegistry.
```

"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class EventHandler[T_Event: BaseModel](ABC):
    """Base class for dependency-injectable event handlers.

    Event handlers should inherit from this class and implement the handle method.
    The generic type parameter specifies which event type this handler processes.

    This pattern enables:
    - Type-safe event handling
    - Constructor dependency injection
    - Organized handler logic in classes
    - Testable handler implementations
    """

    @abstractmethod
    async def handle(self, event: T_Event) -> Any:
        """Handle the event.

        Args:
            event: The event to handle. Must be an instance of the generic type.

        Returns:
            Optional result from handling the event. Can be any type or None.

        Raises:
            Any exception that occurs during handling. Exceptions are caught
            by the event bus and included in the results list.
        """

    def __call__(self, event: T_Event) -> Any:
        """Make the handler callable.

        This allows handler instances to be used directly with the event bus.
        """
        return self.handle(event)


class EventBusError(Exception):
    """Base exception for all event bus related errors.

    This is the root of the event bus exception hierarchy. All specific
    event bus exceptions inherit from this class.

    Use this for catching any event bus related error:
        ```python
        try:
            # event bus operations
            pass
        except EventBusError as e:
            logger.error(f"Event bus error: {e}")
        ```
    """


class HandlerRegistrationError(EventBusError):
    """Raised when handler registration fails.

    This occurs when:
    - The event type is not a Pydantic BaseModel
    - The handler is not callable
    - The handler signature is invalid
    """


class EventEmissionError(EventBusError):
    """Raised when event emission fails.

    This occurs when:
    - The event is not a Pydantic BaseModel instance
    - System errors during emission
    - Invalid event data
    """
