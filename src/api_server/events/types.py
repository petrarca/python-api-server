"""Event type definitions for the API server.

This module contains all Pydantic event models used throughout the system.
Events are the primary way components communicate in a decoupled manner.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PatientCreatedEvent(BaseModel):
    """Event emitted when a new patient is created.

    This event contains basic patient information for logging and
    potential downstream processing.
    """

    patient_id: UUID
    patient_name: str
    created_at: datetime
