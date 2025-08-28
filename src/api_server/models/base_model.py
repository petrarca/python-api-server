from datetime import date
from uuid import UUID

from pydantic import computed_field
from sqlalchemy import ARRAY, String
from sqlmodel import Field, SQLModel


class AddressBase(SQLModel):
    """Base model for an address."""

    id: UUID | None = None
    patient_id: UUID | None = None
    address_type: str | None = None
    address_line: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None


class PatientBase(SQLModel):
    """Base model for a patient."""

    id: UUID | None = None
    patient_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_type: str | None = None
    height: str | None = None
    weight: str | None = None
    primary_address_id: UUID | None = None
    primary_physician: str | None = None
    insurance_provider: str | None = None
    insurance_number: str | None = None
    phone: str | None = None
    email: str | None = None
    conditions: list[str] = Field(sa_type=ARRAY(String), default_factory=list)
    allergies: list[str] = Field(sa_type=ARRAY(String), default_factory=list)

    @computed_field
    def age(self) -> int | None:
        """Calculate age based on date of birth."""
        if not self.date_of_birth:
            return None
        today = date.today()
        born = self.date_of_birth
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return age
