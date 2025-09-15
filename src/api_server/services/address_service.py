"""Address service module."""

import logging
from functools import lru_cache
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import Session, select

from api_server.models.api_model import AddressInput, AddressResponse
from api_server.models.db_model import Address as AddressModel
from api_server.models.db_model import Patient as PatientModel
from api_server.settings import Settings, get_settings
from api_server.utils.model_converter import to_response_model

logger = logging.getLogger(__name__)


class AddressService:
    """Service for address operations.

    Settings can be used for feature flags or limits (placeholder for future).
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def get_addresses(self, session: Session, patient_id: UUID) -> list[AddressResponse]:
        """Get all addresses for a patient."""
        stmt = select(AddressModel).where(AddressModel.patient_id == patient_id)
        addresses = session.exec(stmt).all()

        return [to_response_model(address, AddressResponse) for address in addresses]

    def create_address(self, session: Session, address: AddressInput) -> AddressResponse | None:
        """Create a new address for a patient."""
        if not address.patient_id:
            return None

        try:
            # Create a new address model from the AddressBase object
            address_dict = address.model_dump()
            new_address = AddressModel(**address_dict)

            # Add the patient to the session and commit
            session.add(new_address)
            session.commit()

            # Refresh the address to get the generated ID and other default values
            session.refresh(new_address)

            return to_response_model(new_address, AddressResponse)
        except Exception as e:
            logger.error(f"Service: create_address - failed to create address: {e}")
            session.rollback()
            return None

    def update_address(self, session: Session, id_: UUID, address: AddressInput) -> AddressResponse | None:
        """Update an address for a patient."""

        try:
            # Find the address
            stmt = select(AddressModel).where(AddressModel.id == id_)
            existing_address = session.exec(stmt).first()

            if not existing_address:
                logger.debug(f"Service: update_address - address not found: {id_}")
                return None

            # Update all fields from the address object, excluding patient_id
            address_data = address.model_dump(exclude={"patient_id"})

            # Update the existing patient directly with the dictionary
            existing_address.sqlmodel_update(address_data)

            # Commit the changes
            session.commit()

            # Refresh the address from the database
            session.refresh(existing_address)

            logger.debug(f"Service: update_address - successfully updated address {id_}")
            return to_response_model(existing_address, AddressResponse)
        except Exception as e:
            logger.error(f"Service: update_address - failed to update address: {e}")
            session.rollback()
            return None

    def delete_address(self, session: Session, address_id: UUID) -> bool:
        """Delete an address."""
        logger.debug(f"Service: delete_address with address_id={address_id}")

        try:
            # First, find the patient_id for this address
            stmt = select(AddressModel.patient_id).where(AddressModel.id == address_id)
            result = session.exec(stmt).first()

            if not result:
                logger.warning(f"Service: delete_address - address not found: {address_id}")
                return False

            patient_id = result

            # Check if this is the primary address for the patient
            stmt = select(PatientModel).where((PatientModel.id == patient_id) & (PatientModel.primary_address_id == address_id))
            patient = session.exec(stmt).first()

            # If this is the primary address, set primary_address_id to None
            if patient:
                logger.debug(f"Service: delete_address - address {address_id} is the primary address, setting primary_address_id to None")
                patient.primary_address_id = None
                session.add(patient)

            # Now delete the address
            result = session.exec(delete(AddressModel).where(AddressModel.id == address_id))
            session.commit()

            # Check if any rows were affected
            if result.rowcount > 0:
                logger.debug(f"Service: delete_address - successfully deleted address {address_id}")
                return True
            else:
                logger.debug(f"Service: delete_address - address not found: {address_id}")
                return False
        except Exception as e:
            logger.error(f"Service: delete_address - failed to delete address: {e}")
            session.rollback()
            return False


@lru_cache
def get_address_service() -> AddressService:
    """Get the address service singleton using global settings."""
    return AddressService(get_settings())
