from datetime import datetime
from uuid import UUID, uuid7

import arrow
from sqlmodel import Field, Relationship

from api_server.models.base_model import AddressBase, PatientBase


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime using arrow.

    Avoids deprecated datetime.utcnow() (deprecated since Python 3.12).
    """
    return arrow.utcnow().datetime


class Address(AddressBase, table=True):
    """Address model."""

    __tablename__ = "addresses"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    patient_id: UUID = Field(foreign_key="patients.id", default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationship to patient
    patient: Patient = Relationship(back_populates="addresses", sa_relationship_kwargs={"foreign_keys": "[Address.patient_id]"})


class Patient(PatientBase, table=True):
    """Patient model."""

    __tablename__ = "patients"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    patient_id: str = Field(unique=True)
    primary_address_id: UUID | None = Field(
        default=None, foreign_key="addresses.id", sa_column_kwargs={"name": "primary_address"}
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    addresses: list[Address] = Relationship(
        back_populates="patient", sa_relationship_kwargs={"foreign_keys": "[Address.patient_id]"}
    )
    primary_address: Address = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Patient.primary_address_id == Address.id",
            "foreign_keys": "[Patient.primary_address_id]",
        }
    )
