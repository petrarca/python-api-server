from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from api_server.models.base_model import AddressBase, PatientBase


class Address(AddressBase, table=True):
    """Address model."""

    __tablename__ = "addresses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    patient_id: UUID = Field(foreign_key="patients.id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to patient
    patient: "Patient" = Relationship(back_populates="addresses", sa_relationship_kwargs={"foreign_keys": "[Address.patient_id]"})


class Patient(PatientBase, table=True):
    """Patient model."""

    __tablename__ = "patients"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    patient_id: str = Field(unique=True)
    primary_address_id: UUID | None = Field(default=None, foreign_key="addresses.id", sa_column_kwargs={"name": "primary_address"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    addresses: list["Address"] = Relationship(back_populates="patient", sa_relationship_kwargs={"foreign_keys": "[Address.patient_id]"})
    primary_address: "Address" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Patient.primary_address_id == Address.id", "foreign_keys": "[Patient.primary_address_id]"}
    )
