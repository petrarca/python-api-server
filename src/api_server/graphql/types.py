"""GraphQL types for the API server."""

import strawberry

from api_server.models.api_model import (
    AddressInput,
    AddressResponse,
    PatientCreateInput,
    PatientCreateResponse,
    PatientInput,
    PatientResponse,
)
from api_server.services.address_service import AddressService


@strawberry.experimental.pydantic.type(
    model=AddressResponse,
    all_fields=True,
)
class Address:
    """GraphQL type for an address."""

    @strawberry.field
    def id(self) -> str:
        """Get address ID."""
        return str(self.id)

    @strawberry.field
    def patient_id(self) -> str:
        """Get address ID."""
        return str(self.patient_id)


@strawberry.experimental.pydantic.type(
    model=AddressInput,
    is_input=True,
    all_fields=True,
)
class AddressInput:
    """GraphQL input type for address creation and updates."""


@strawberry.experimental.pydantic.type(
    model=PatientResponse,
    all_fields=True,
)
class Patient:
    """GraphQL type for a patient."""

    @strawberry.field
    def id(self) -> str:
        """Get patient ID."""
        return str(self.id)

    @strawberry.field
    def age(self) -> int | None:
        """Get patient age calculated from date of birth."""
        return self.age

    # Test only, will be handled in query to optimize loading (N+1)
    @strawberry.field
    def addresses(self, info: strawberry.Info) -> list[Address]:
        """Get addresses for this patient."""
        address_service = info.context.service(AddressService)
        session = info.context.db_session
        return address_service.get_addresses(session, self.id)


@strawberry.experimental.pydantic.type(
    model=PatientCreateResponse,
    all_fields=True,
)
class PatientCreate:
    """GraphQL type for a patient create, patient with addresses."""


@strawberry.experimental.pydantic.type(
    model=PatientInput,
    is_input=True,
    all_fields=True,
)
class PatientInput:
    """GraphQL input type for patient creation and updates."""

    pass


@strawberry.experimental.pydantic.type(
    model=PatientCreateInput,
    is_input=True,
    all_fields=True,
)
class PatientCreateInput:
    """GraphQL input type for patient creation and updates."""

    pass
