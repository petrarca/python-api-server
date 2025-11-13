"""Service for patient-related operations."""

from functools import lru_cache
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, update
from sqlmodel import Session, select

from api_server.models.api_model import AddressResponse, PatientCreateInput, PatientCreateResponse, PatientInput, PatientResponse
from api_server.models.db_model import Address as AddressModel
from api_server.models.db_model import Patient as PatientModel
from api_server.services.address_service import get_address_service
from api_server.utils.id_generator import generate_short_id
from api_server.utils.model_converter import to_response_model


class PatientService:
    """Service for patient-related operations."""

    def __init__(self):
        """Initialize the patient service."""
        self.address_service = get_address_service()

    def get_patient_by_id(
        self, session: Session, id_: UUID | None = None, patient_id: str | None = None
    ) -> PatientResponse | None:
        """Get a patient by ID.

        Args:
            session: Database session
            id_: UUID of the patient to retrieve
            patient_id: Alternative patient identifier

        Returns:
            PatientResponse if found, None otherwise
        """
        logger.debug(f"Service: get_patient_by_id with id_={id_}, patient_id={patient_id}")
        if id_ is not None:
            stmt = select(PatientModel).where(PatientModel.id == id_)
        elif patient_id is not None:
            stmt = select(PatientModel).where(PatientModel.patient_id == patient_id)
        else:
            return None

        patient = session.exec(stmt).first()
        logger.debug(f"Service: get_patient_by_id result: {'found' if patient else 'not found'}")

        # Convert PatientModel to PatientResponse before returning
        return to_response_model(patient, PatientResponse)

    def update_primary_address(self, session: Session, id_: UUID, address_id: UUID | None) -> UUID | None:
        """Update a patient's primary address.

        Args:
            session: Database session
            id_: UUID of the patient to update
            address_id: UUID of the new primary address

        Returns:
            UUID of the new primary address or None if update failed
        """
        logger.debug(f"Service: update_primary_address with id={id_}, address_id={address_id}")

        # First, check if the patient exists and get the current primary_address_id for optimistic locking
        stmt = select(PatientModel.id, PatientModel.primary_address_id).where(PatientModel.id == id_)
        result = session.exec(stmt).first()

        if not result:
            logger.warning(f"Service: update_primary_address - patient not found: {id_}")
            return None

        current_primary_address_id = result.primary_address_id

        # If setting a new address, verify it belongs to this patient
        if address_id is not None:
            stmt = select(AddressModel.id).where((AddressModel.id == address_id) & (AddressModel.patient_id == id_))
            address = session.exec(stmt).first()
            if not address:
                logger.warning(f"Service: update_primary_address - address not found or doesn't belong to patient: {address_id}")
                return None

        # Update the primary address with optimistic locking using a direct UPDATE statement
        # Only update if the current primary_address_id matches what we retrieved earlier
        stmt = (
            update(PatientModel)
            .where((PatientModel.id == id_) & (PatientModel.primary_address_id == current_primary_address_id))
            .values(primary_address_id=address_id)
        )
        result = session.exec(stmt)
        rows_updated = result.rowcount
        session.commit()

        if rows_updated == 0:
            logger.debug("Service: update_primary_address - optimistic lock failed, primary address may have changed")
            return None

        logger.debug(f"Service: update_primary_address - successfully updated primary address to {address_id}")
        return address_id

    def create_patient(self, session: Session, patient: PatientCreateInput) -> PatientCreateResponse | None:
        """Create a new patient.

        Args:
            session: Database session
            patient: PatientCreateInput object containing patient information, with addresses

        Returns:
            PatientResponse object or None if creation failed
        """
        logger.debug(f"Service: create_patient - creating patient with name {patient.first_name} {patient.last_name}")

        try:
            # Generate a unique patient_id if not provided
            patient_id = patient.patient_id or None
            if not patient_id:
                patient.patient_id = f"P{generate_short_id(8)}"

            # Create a new patient model from the PatientBase object
            patient_dict = patient.model_dump()
            # Extract and remove addresses from patient_dict
            addresses = patient_dict.pop("addresses", [])
            new_patient = PatientModel(**patient_dict)

            # Add the patient to the session
            session.add(new_patient)

            # Create addresses for the patient if any are provided
            if addresses:
                for address_data in addresses:
                    # Create a new address model
                    new_address = AddressModel(**address_data)
                    # Add the address to the patient's addresses relationship
                    # This will automatically set the patient_id and add the address to the session
                    new_patient.addresses.append(new_address)

            # Commit all changes at once
            session.commit()

            # Refresh the patient to get the generated ID and other default values
            session.refresh(new_patient)

            # Create the patient response
            patient_response = to_response_model(new_patient, PatientCreateResponse, {"addresses": AddressResponse})
            logger.debug(f"Service: create_patient - successfully created patient with ID {new_patient.id}")
            return patient_response
        except Exception as e:
            logger.error(f"Service: create_patient - failed to create patient: {e}")
            session.rollback()
            return None

    def update_patient(self, session: Session, id_: UUID, patient: PatientInput) -> PatientResponse | None:
        """Update a patient.

        Args:
            session: Database session
            id_: UUID of the patient to update
            patient: PatientInput object containing updated patient information

        Returns:
            PatientResponse object or None if update failed
        """
        logger.debug(f"Service: update_patient with id={id_}")

        try:
            # Find the patient
            stmt = select(PatientModel).where(PatientModel.id == id_)
            existing_patient = session.exec(stmt).first()

            if not existing_patient:
                logger.debug(f"Service: update_patient - patient not found: {id_}")
                return None

            # Update all fields from the patient object
            patient_data = patient.model_dump()

            # Update the existing patient directly with the dictionary
            existing_patient.sqlmodel_update(patient_data)

            # Commit the changes
            session.commit()

            # Refresh the patient from the database
            session.refresh(existing_patient)

            logger.debug(f"Service: update_patient - successfully updated patient {id_}")
            return to_response_model(existing_patient, PatientResponse)

        except Exception as e:
            logger.error(f"Service: update_patient - failed to update patient: {e}")
            session.rollback()
            return None

    def delete_patient(self, session: Session, id_: UUID) -> bool:
        """Delete a patient by ID.

        Args:
            session: Database session
            id_: UUID of the patient to delete

        Returns:
            True if patient was successfully deleted, False otherwise
        """
        logger.debug(f"Service: delete_patient with id={id_}")

        try:
            # Execute delete statement directly with where condition
            stmt = delete(PatientModel).where(PatientModel.id == id_)
            result = session.exec(stmt)

            # Commit the transaction
            session.commit()

            # Check if any rows were affected
            rows_deleted = result.rowcount
            if rows_deleted == 0:
                logger.debug(f"Service: delete_patient - patient not found: {id_}")
                return False

            logger.debug(f"Service: delete_patient - successfully deleted patient {id_}")
            return True

        except Exception as e:
            logger.error(f"Service: delete_patient - failed to delete patient: {e}")
            session.rollback()
            return False

    def get_most_recent_changed_patients(self, session: Session, limit: int = 10) -> list[PatientResponse]:
        """Get the most recently updated patients.

        Args:
            session: Database session
            limit: Number of patients to return

        Returns:
            List of PatientResponse objects
        """
        logger.debug(f"Service: get_most_recent_changed_patients with limit={limit}")

        try:
            # Query patients ordered by updated_at descending with limit
            stmt = select(PatientModel).order_by(PatientModel.updated_at.desc()).limit(limit)
            patients = session.exec(stmt).all()

            logger.debug(f"Service: get_most_recent_changed_patients found {len(patients)} patients")
            # Convert each PatientModel to PatientResponse
            return [to_response_model(patient, PatientResponse) for patient in patients]
        except Exception as e:
            logger.error(f"Service: get_most_recent_changed_patients - failed to fetch patients: {e}")
            return []


@lru_cache
def get_patient_service() -> PatientService:
    """Get the patient service singleton.

    The @lru_cache decorator ensures this functions as a singleton,
    returning the same instance for all calls.

    Returns:
        PatientService: The singleton patient service instance
    """
    return PatientService()
