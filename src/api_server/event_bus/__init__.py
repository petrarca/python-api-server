"""Event Bus System for Decoupled Component Communication.

This module provides a framework-agnostic event bus that enables loose coupling
between different components in your application. It supports:

- **Pydantic Event Models**: Type-safe event definitions using BaseModel
- **Async Handler Execution**: All handlers run asynchronously and concurrently
- **Dependency Injection**: Handlers can receive dependencies via constructor injection
- **Error Isolation**: Handler failures don't affect other handlers
- **Singleton Pattern**: Global event bus instance via @lru_cache

## Quick Start

```python
from api_server.event_bus.bus import EventBus, get_event_bus
from pydantic import BaseModel

# Define an event
class UserCreatedEvent(BaseModel):
    user_id: int
    email: str

# Create a simple function handler
async def send_welcome_email(event: UserCreatedEvent) -> None:
    print(f"Sending welcome email to {event.email}")

# Register and emit
bus = get_event_bus()
bus.on(UserCreatedEvent, send_welcome_email)
await bus.emit(UserCreatedEvent(user_id=1, email="user@example.com"))
```

## Architecture

The event bus follows a decoupled architecture where:
- **Event Bus Core**: Framework-agnostic event management
- **Event Definitions**: Domain-specific Pydantic models
- **Event Handlers**: Business logic for processing events

This design allows the same event bus to be used across different
contexts (FastAPI, GraphQL, MCP) without framework dependencies.

For class-based handlers with dependency injection, see `core.py`.
For advanced usage and API reference, see `bus.py`.

"""

from .bus import EventBus, get_event_bus
from .core import EventHandler

__all__ = [
    "EventBus",
    "EventHandler",
    "get_event_bus",
]
