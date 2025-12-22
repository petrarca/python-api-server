"""Patient-related event handlers.

This module contains handlers that respond to patient events.
"""

from loguru import logger

from api_server.event_bus.core import EventHandler
from api_server.events.types import PatientCreatedEvent


class PatientCreatedEventHandler(EventHandler[PatientCreatedEvent]):
    """Handler for PatientCreatedEvent that logs patient creation.

    This is a simple example handler that demonstrates how to use
    the event bus system. It logs when a new patient is created.
    """

    def handle(self, event: PatientCreatedEvent) -> None:
        """Handle the PatientCreatedEvent.

        Args:
            event: The patient created event containing patient information
        """
        logger.info(f"🎉 New patient created: {event.patient_name} (ID: {event.patient_id})")
        logger.info(f"   Created at: {event.created_at}")

        # Here you could add additional logic like:
        # - Sending notifications
        # - Updating analytics
        # - Triggering workflows
        # - Synchronizing with external systems
