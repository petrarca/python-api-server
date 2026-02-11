"""Event Bus Implementation.

This module provides the main EventBus class that handles event registration
and emission. The event bus is framework-agnostic and can be used in any
async Python application.

## Key Features

- **Async Handler Execution**: All handlers execute concurrently
- **ServiceRegistry Integration**: Uses server's DI system for handler dependencies
- **Error Isolation**: Handler failures don't affect other handlers
- **Type Safety**: Strong typing with Pydantic events
- **Singleton Pattern**: Global instance via @lru_cache

## Advanced Usage

```python
from api_server.event_bus import get_event_bus
from pydantic import BaseModel

# Define events
class OrderCreatedEvent(BaseModel):
    order_id: str
    customer_id: str

class PaymentProcessedEvent(BaseModel):
    order_id: str
    amount: float

# Register multiple handlers
async def update_inventory(event: OrderCreatedEvent) -> None:
    # Update inventory logic
    pass

async def send_confirmation(event: OrderCreatedEvent) -> None:
    # Send email confirmation
    pass

bus = get_event_bus()
bus.on(OrderCreatedEvent, update_inventory)
bus.on(OrderCreatedEvent, send_confirmation)

# Emit and wait for results
results = await bus.emit_and_wait(
    OrderCreatedEvent(order_id="123", customer_id="cust_456")
)
print(f"Handler results: {results}")

# Emit with error isolation
results = await bus.emit_and_wait(
    OrderCreatedEvent(order_id="789", customer_id="cust_101"),
    isolate_events=True  # Each handler gets a copy of the event
)
```

"""

import asyncio
import concurrent.futures
import inspect
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

from loguru import logger
from pydantic import BaseModel

from .core import HandlerRegistrationError

T_Event = TypeVar("T_Event", bound=BaseModel)
T_Handler = Callable[..., Any]


class EventBus:
    """Framework-agnostic event bus for async event handling.

    The EventBus provides a decoupled way to handle events in your application.
    It supports both function and class-based handlers, uses ServiceRegistry
    for dependency injection, and ensures error isolation between handlers.

    Example:
        ```python
        bus = get_event_bus()
        bus.on(UserCreatedEvent, send_welcome_email)
        bus.emit(UserCreatedEvent(user_id=1, email="user@example.com"))
        # Or wait for results:
        results = await bus.emit_and_wait(UserCreatedEvent(user_id=1, email="user@example.com"))
        ```
    """

    def __init__(self, isolate_events: bool = False) -> None:
        """Initialize a new EventBus instance.

        Args:
            isolate_events: If True, each handler receives a deep copy of the event.
                           Can be overridden per emit() call. Default is False.
        """
        self._handlers: dict[type[BaseModel], list[T_Handler]] = {}
        self._isolate_events = isolate_events
        self._sync_executor: concurrent.futures.ThreadPoolExecutor | None = None
        logger.debug(f"EventBus initialized (isolate_events={isolate_events})")

    def on(self, event_type: type[T_Event], handler: T_Handler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The Pydantic BaseModel class to handle
            handler: The handler function or class instance

        Raises:
            HandlerRegistrationError: If event_type is not BaseModel or handler is not callable
        """
        # Validate event type
        if not (isinstance(event_type, type) and issubclass(event_type, BaseModel)):
            raise HandlerRegistrationError(f"Event type must be a Pydantic BaseModel subclass, got: {event_type}")

        # Validate handler
        if not callable(handler):
            raise HandlerRegistrationError(f"Handler must be callable: {handler}")

        # Register handler
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.__name__}: {handler}")

    def remove_handler(self, event_type: type[T_Event], handler: T_Handler) -> bool:
        """Remove a specific handler for an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Removed handler for {event_type.__name__}: {handler}")
                return True
            except ValueError:
                pass
        return False

    def clear_handlers(self, event_type: type[T_Event] | None = None) -> None:
        """Clear handlers for a specific event type or all events."""
        if event_type is None:
            self._handlers.clear()
            logger.debug("Cleared all handlers")
        elif event_type in self._handlers:
            del self._handlers[event_type]
            logger.debug(f"Cleared handlers for {event_type.__name__}")

    def get_handler_count(self, event_type: type[T_Event]) -> int:
        """Get the number of handlers registered for an event type."""
        return len(self._handlers.get(event_type, []))

    def get_registered_events(self) -> list[type[BaseModel]]:
        """Get all event types that have registered handlers.

        Returns:
            List of event types with handlers

        Example:
            ```python
            events = bus.get_registered_events()
            for event_type in events:
                print(f"Event: {event_type.__name__}")
            ```
        """
        return list(self._handlers.keys())

    def emit(self, event: T_Event, isolate: bool | None = None) -> None:
        """Emit an event without waiting for completion (fire-and-forget).

        This method creates a task for event emission and returns immediately.
        Use this when you don't need to wait for handlers to complete.

        Args:
            event: The event to emit
            isolate: Whether to isolate events (deep copy per handler)
        """
        asyncio.create_task(self.emit_and_wait(event, isolate))

    def emit_sync(self, event: T_Event, isolate: bool | None = None) -> list[Any]:
        """Emit an event synchronously and wait for all handlers to complete.

        Use this when calling from a synchronous context (e.g., readiness checks)
        where you need to wait for handlers to finish before continuing.

        Args:
            event: The event instance to emit
            isolate: If True, each handler receives a deep copy of the event.

        Returns:
            List of results from all handlers (including exceptions)
        """
        try:
            asyncio.get_running_loop()
            # We're inside an async context - use thread pool to run the coroutine
            if self._sync_executor is None:
                self._sync_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                logger.debug("Created sync executor for EventBus")
            future = self._sync_executor.submit(asyncio.run, self.emit_and_wait(event, isolate))
            return future.result()
        except RuntimeError:
            # No running loop - we can use asyncio.run directly
            return asyncio.run(self.emit_and_wait(event, isolate))

    def shutdown(self) -> None:
        """Shutdown the EventBus and release resources.

        Call this during application shutdown to cleanly release the thread pool
        used for synchronous event emission.
        """
        if self._sync_executor is not None:
            logger.debug("Shutting down EventBus sync executor")
            self._sync_executor.shutdown(wait=True)
            self._sync_executor = None
        logger.debug("EventBus shutdown complete")

    async def emit_and_wait(self, event: T_Event, isolate: bool | None = None) -> list[Any]:
        """Emit an event and wait for all handlers to complete.

        Args:
            event: The event instance to emit
            isolate: If True, each handler receives a deep copy of the event.
                    If None (default), uses the bus-level setting.

        Returns:
            List of results from all handlers (including exceptions)

        Raises:
            EventEmissionError: If event is not a BaseModel instance
        """
        # Validate that event is a BaseModel instance
        if not isinstance(event, BaseModel):
            from .core import EventEmissionError

            raise EventEmissionError(f"Event must be a BaseModel instance, got: {type(event).__name__}")

        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers registered for {event_type.__name__}")
            return []

        logger.debug(f"Emitting {event_type.__name__} to {len(handlers)} handlers")

        # Determine if events should be isolated (copied for each handler)
        should_isolate = isolate if isolate is not None else self._isolate_events
        logger.trace(f"Event isolation: {should_isolate} (isolate={isolate}, bus_default={self._isolate_events})")

        # Execute all handlers concurrently
        tasks = []
        for i, handler in enumerate(handlers):
            # If isolating, create a deep copy for each handler
            handler_event = event.model_copy(deep=True) if should_isolate else event
            logger.trace(f"Creating task for handler {i + 1}/{len(handlers)}: {handler}")
            task = self._execute_handler(handler, handler_event)
            tasks.append(task)

        logger.trace(f"Executing {len(tasks)} handlers concurrently")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(f"Event {event_type.__name__} processed, {len(results)} results")

        # Log result summary
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        if failed > 0:
            logger.warning(f"Event {event_type.__name__}: {successful} successful, {failed} failed handlers")
        logger.trace(f"Event {event_type.__name__} results: {results}")

        return results

    async def _execute_handler(self, handler: T_Handler, event: T_Event) -> Any:
        """Execute a single handler with dependency injection.

        Args:
            handler: The handler to execute (function or class)
            event: The event to pass to the handler

        Returns:
            The handler's result or any exception raised
        """
        try:
            logger.trace(f"Executing handler {handler} for event {type(event).__name__}")

            # If handler is a class, instantiate it with DI and call handle method
            if inspect.isclass(handler):
                handler_instance = self._instantiate_handler_class(handler)
                handler_method = getattr(handler_instance, "handle", None)
                if handler_method is None:
                    raise AttributeError(f"Handler class {handler.__name__} must have a 'handle' method")
                return await handler_method(event)

            # For function handlers, check if they accept dependencies
            sig = inspect.signature(handler)
            parameters = list(sig.parameters.values())
            logger.trace(f"Handler signature: {sig}")

            # If handler only takes the event, call directly
            if len(parameters) <= 1:
                logger.trace(f"Calling handler {handler} with event only")
                result = await handler(event)
                logger.trace(f"Handler {handler} completed successfully")
                return result

            # Try to inject dependencies from ServiceRegistry
            kwargs = {}
            try:
                from api_server.services.registry import get_service_registry

                registry = get_service_registry()

                for param in parameters[1:]:  # Skip first parameter (event)
                    try:
                        # Try to get service by type annotation
                        if param.annotation != inspect.Parameter.empty:
                            service = registry.get(param.annotation)
                            kwargs[param.name] = service
                            logger.trace(f"Injected service '{param.annotation.__name__}' for handler {handler}")
                    except KeyError, AttributeError:
                        logger.trace(f"Service '{param.annotation}' not found in registry for handler {handler}")

            except ImportError:
                logger.trace("ServiceRegistry not available, running without DI")

            logger.trace(f"Calling handler {handler} with event and {len(kwargs)} dependencies")
            result = await handler(event, **kwargs)
            logger.trace(f"Handler {handler} completed successfully")
            return result

        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Handler {handler} failed: {e}")
            logger.trace(f"Handler {handler} exception details: {type(e).__name__}: {e}")
            return e

    def _instantiate_handler_class(self, handler_class: type) -> Any:
        """Instantiate a handler class with dependency injection.

        Args:
            handler_class: The handler class to instantiate

        Returns:
            An instance of the handler class with dependencies injected
        """
        try:
            # Get the __init__ signature
            sig = inspect.signature(handler_class.__init__)
            parameters = list(sig.parameters.values())[1:]  # Skip 'self'

            # If no parameters, instantiate directly
            if not parameters:
                return handler_class()

            # Try to inject dependencies
            kwargs = {}
            try:
                from api_server.services.registry import get_service_registry

                registry = get_service_registry()

                for param in parameters:
                    try:
                        # Try to get service by type annotation
                        if param.annotation != inspect.Parameter.empty:
                            service = registry.get(param.annotation)
                            kwargs[param.name] = service
                            logger.trace(
                                f"Injected service '{param.annotation.__name__}' into handler class {handler_class.__name__}"
                            )
                    except KeyError, AttributeError:
                        logger.trace(f"Service '{param.annotation}' not found for handler class {handler_class.__name__}")

            except ImportError:
                logger.trace("ServiceRegistry not available, instantiating without DI")

            return handler_class(**kwargs)

        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Failed to instantiate handler class {handler_class.__name__}: {e}")
            raise


@lru_cache
def get_event_bus() -> EventBus:
    """Get or create the singleton EventBus instance.

    Returns:
        The EventBus instance

    Example:
        ```python
        bus = get_event_bus()
        bus.on(MyEvent, my_handler)
        await bus.emit_and_wait(MyEvent(data="test"))
        ```
    """
    return EventBus()
