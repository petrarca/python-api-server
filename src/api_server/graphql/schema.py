"""GraphQL schema for API server."""

from uuid import UUID

import strawberry
from loguru import logger

from api_server.graphql.types import (
    Address,
    AddressInput,
    Patient,
    PatientCreate,
    PatientCreateInput,
    PatientInput,
)
from api_server.services.address_service import AddressService
from api_server.services.patient_service import PatientService


@strawberry.type
class Query:
    """Root query type for the GraphQL schema."""

    @strawberry.field
    async def patient(
        self,
        info: strawberry.Info,
        id: UUID | None = None,
        patient_id: str | None = None,
    ) -> Patient | None:
        """Get a patient by ID.

        Args:
            info: GraphQL resolver info
            id: UUID of the patient to retrieve
            patient_id: Alternative patient identifier

        Returns:
            Patient object if found, None otherwise
        """
        logger.debug(f"GraphQL query: patient with id={id}, patient_id={patient_id}")
        from api_server.services.patient_service import PatientService

        patient_service = info.context.service(PatientService)
        session = info.context.db_session
        patient = patient_service.get_patient_by_id(session, id, patient_id)
        return patient

    @strawberry.field
    async def addresses(self, info: strawberry.Info, patient_id: strawberry.ID) -> list[Address]:
        """Get addresses for a specific patient.

        Args:
            info: GraphQL resolver info
            patient_id: ID of the patient to get addresses for

        Returns:
            List of Address objects associated with the patient
        """
        logger.debug(f"GraphQL query: addresses with id={patient_id}")

        address_service = info.context.service(AddressService)
        session = info.context.db_session
        return address_service.get_addresses(session, patient_id)

    @strawberry.field
    async def most_recent_patients(self, info: strawberry.Info, limit: int | None = 10) -> list[Patient]:
        """Get the most recently updated patients.

        Args:
            info: GraphQL resolver info
            limit: Maximum number of patients to return

        Returns:
            List of most recently updated Patient objects
        """
        logger.debug(f"GraphQL query: most_recent_patients with limit={limit}")

        patient_service = info.context.service(PatientService)
        session = info.context.db_session
        return patient_service.get_most_recent_changed_patients(session, limit=limit)


@strawberry.type
class Mutation:
    """Root mutation type for the GraphQL schema."""

    @strawberry.mutation
    async def update_primary_address(
        self, info: strawberry.Info, id: strawberry.ID, address_id: strawberry.ID | None
    ) -> strawberry.ID | None:
        """Update a patient's primary address.

        Args:
            info: GraphQL resolver info
            id: ID of the patient to update
            address_id: ID of the new primary address

        Returns:
            ID of the updated primary address, or None if not updated
        """
        logger.debug(f"GraphQL mutation: update_primary_address with patient_id={id}, address_id={address_id}")

        patient_service = info.context.service(PatientService)
        session = info.context.db_session

        # Convert string IDs to UUID
        patient_uuid = UUID(str(id))
        address_uuid = UUID(str(address_id)) if address_id is not None else None

        # Update the primary address
        result_address_id = patient_service.update_primary_address(session, patient_uuid, address_uuid)

        logger.debug(f"GraphQL mutation result: update_primary_address returned {result_address_id}")
        # Convert UUID back to string ID for GraphQL response
        return str(result_address_id) if result_address_id is not None else None

    @strawberry.mutation
    async def create_address(
        self,
        info: strawberry.Info,
        address: AddressInput,
    ) -> Address | None:
        """Create a new address for a patient.

        Args:
            info: GraphQL resolver info
            address: AddressInput object containing address details

        Returns:
            Created Address object, or None if creation failed
        """
        logger.debug("GraphQL mutation: create_address")

        from api_server.services.address_service import AddressService

        address_service = info.context.service(AddressService)
        session = info.context.db_session

        # Create the address
        result = address_service.create_address(session, address.to_pydantic())

        logger.debug(f"GraphQL mutation result: create_address returned {result}")
        return result

    @strawberry.mutation
    async def update_address(
        self,
        info: strawberry.Info,
        address_id: strawberry.ID,
        address: AddressInput,
    ) -> Address | None:
        """Update an address for a patient.

        Args:
            info: GraphQL resolver info
            address_id: ID of the address to update
            address: AddressInput object containing updated address details

        Returns:
            Updated Address object, or None if update failed
        """
        logger.debug(f"GraphQL mutation: update_address with address_id={address_id}")

        address_service = info.context.service(AddressService)
        session = info.context.db_session

        # Convert string IDs to UUID
        address_uuid = UUID(str(address_id))

        # Update the address
        result = address_service.update_address(session, address_uuid, address.to_pydantic())

        logger.debug(f"GraphQL mutation result: update_address returned {result}")
        return result

    @strawberry.mutation
    async def delete_address(self, info: strawberry.Info, address_id: strawberry.ID) -> bool:
        """Delete an address for a patient.

        Args:
            info: GraphQL resolver info
            address_id: ID of the address to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.debug(f"GraphQL mutation: delete_address with address_id={address_id}")

        address_service = info.context.service(AddressService)
        session = info.context.db_session

        # Convert string IDs to UUID
        address_uuid = UUID(str(address_id))

        # Delete the address
        result = address_service.delete_address(session, address_uuid)

        logger.debug(f"GraphQL mutation result: delete_address returned {result}")
        return result

    @strawberry.mutation
    async def create_patient(
        self,
        info: strawberry.Info,
        patient: PatientCreateInput,
    ) -> PatientCreate | None:
        """Create a new patient.

        Args:
            info: GraphQL resolver info
            patient: PatientInput object containing patient details

        Returns:
            Created Patient object, or None if creation failed
        """
        logger.debug("GraphQL mutation: create_patient")

        patient_service = info.context.service(PatientService)
        session = info.context.db_session

        # Convert to pydantic model and create patient
        result = patient_service.create_patient(session, patient.to_pydantic())

        logger.debug(f"GraphQL mutation result: create_patient returned {result}")
        return result

    @strawberry.mutation
    async def update_patient(
        self,
        info: strawberry.Info,
        id: strawberry.ID,
        patient: PatientInput,
    ) -> Patient | None:
        """Update a patient.

        Args:
            info: GraphQL resolver info
            id: ID of the patient to update
            patient: PatientInput object containing updated patient details

        Returns:
            Updated Patient object, or None if update failed
        """
        logger.debug(f"GraphQL mutation: update_patient with id={id}")

        patient_service = info.context.service(PatientService)
        session = info.context.db_session

        # Convert string ID to UUID
        id_ = UUID(str(id))

        # Convert to pydantic model and then update
        result = patient_service.update_patient(session, id_, patient.to_pydantic())

        logger.debug(f"GraphQL mutation result: update_patient returned {result}")
        return result

    @strawberry.mutation
    async def delete_patient(
        self,
        info: strawberry.Info,
        id: strawberry.ID,
    ) -> bool:
        """Delete a patient by ID.

        Args:
            info: GraphQL resolver info
            id: ID of the patient to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.debug(f"GraphQL mutation: delete_patient with id={id}")

        patient_service = info.context.service(PatientService)
        session = info.context.db_session

        # Convert string ID to UUID
        id_ = UUID(str(id))

        # Delete the patient
        result = patient_service.delete_patient(session, id_)

        logger.debug(f"GraphQL mutation result: delete_patient returned {result}")
        return result


schema = strawberry.Schema(query=Query, mutation=Mutation)
