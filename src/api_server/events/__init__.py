"""Event system for the API server.

This module provides event types and handlers for decoupled communication
between components in the system.
"""

from loguru import logger

from api_server.event_bus import get_event_bus
from api_server.events.patient_handlers import PatientCreatedEventHandler
from api_server.events.types import PatientCreatedEvent

__all__ = [
    "PatientCreatedEvent",
    "PatientCreatedEventHandler",
]


def register_event_handlers() -> None:
    """Register event handlers in the event bus.

    This sets up the event-driven architecture by registering handlers
    that respond to various events emitted by the system.
    """
    logger.debug("Registering event handlers in event bus")

    # Get event bus and register handlers
    event_bus = get_event_bus()

    # Register patient event handler
    event_bus.on(PatientCreatedEvent, PatientCreatedEventHandler)

    logger.info("Event handlers registered successfully")


# Event handlers will be registered explicitly after ServiceRegistry initialization
