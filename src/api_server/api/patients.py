"""
Patient API - CRUD operations for patient management.

This module provides REST endpoints for managing patients:
- CRUD operations: Create, read, update, delete patients
- Address management: Update primary address
- Recent changes: Get most recently updated patients

All endpoints delegate to PatientService for business logic.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from api_server.database import get_db_session
from api_server.models.api_model import (
    PatientCreateInput,
    PatientCreateResponse,
    PatientInput,
    PatientResponse,
    PrimaryAddressUpdate,
)
from api_server.services.patient_service import PatientService, get_patient_service

router = APIRouter()


@router.get("/patients/recent", response_model=list[PatientResponse])
def get_recent_patients(
    limit: int = 10,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> list[PatientResponse]:
    """Get the most recently updated patients.

    Args:
        limit: Number of patients to return (default: 10)
        patient_service: Patient service instance
        session: Database session

    Returns:
        List of PatientResponse objects
    """
    return patient_service.get_most_recent_changed_patients(session, limit)


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: UUID,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> PatientResponse:
    """Get a patient by ID.

    Args:
        patient_id: UUID of the patient to retrieve
        patient_service: Patient service instance
        session: Database session

    Returns:
        PatientResponse object

    Raises:
        HTTPException: If patient not found
    """
    patient = patient_service.get_patient_by_id(session, id_=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found",
        )
    return patient


@router.get("/patients/by-patient-id/{patient_id}", response_model=PatientResponse)
def get_patient_by_patient_id(
    patient_id: str,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> PatientResponse:
    """Get a patient by patient_id string.

    Args:
        patient_id: Patient identifier string
        patient_service: Patient service instance
        session: Database session

    Returns:
        PatientResponse object

    Raises:
        HTTPException: If patient not found
    """
    patient = patient_service.get_patient_by_id(session, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with patient_id {patient_id} not found",
        )
    return patient


@router.post("/patients", response_model=PatientCreateResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient: PatientCreateInput,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> PatientCreateResponse:
    """Create a new patient.

    Args:
        patient: PatientCreateInput object containing patient information
        patient_service: Patient service instance
        session: Database session

    Returns:
        PatientCreateResponse object

    Raises:
        HTTPException: If creation failed
    """
    created_patient = patient_service.create_patient(session, patient)
    if not created_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create patient",
        )
    return created_patient


@router.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: UUID,
    patient: PatientInput,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> PatientResponse:
    """Update a patient.

    Args:
        patient_id: UUID of the patient to update
        patient: PatientInput object containing updated patient information
        patient_service: Patient service instance
        session: Database session

    Returns:
        PatientResponse object

    Raises:
        HTTPException: If patient not found or update failed
    """
    updated_patient = patient_service.update_patient(session, patient_id, patient)
    if not updated_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found or update failed",
        )
    return updated_patient


@router.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: UUID,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> None:
    """Delete a patient by ID.

    Args:
        patient_id: UUID of the patient to delete
        patient_service: Patient service instance
        session: Database session

    Raises:
        HTTPException: If patient not found or deletion failed
    """
    success = patient_service.delete_patient(session, patient_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found or deletion failed",
        )


@router.put("/patients/{patient_id}/primary-address", response_model=dict)
def update_primary_address(
    patient_id: UUID,
    body: PrimaryAddressUpdate,
    patient_service: PatientService = Depends(get_patient_service),
    session: Session = Depends(get_db_session),
) -> dict:
    """Update a patient's primary address.

    Args:
        patient_id: UUID of the patient to update
        body: Request body containing address_id (UUID of new primary address, or null to clear)
        patient_service: Patient service instance
        session: Database session

    Returns:
        Dictionary with updated address_id

    Raises:
        HTTPException: If patient not found or update failed
    """
    address_id = body.address_id
    updated_address_id = patient_service.update_primary_address(session, patient_id, address_id)
    if updated_address_id is None and address_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to update primary address - patient or address not found",
        )
    return {"patient_id": str(patient_id), "primary_address_id": str(updated_address_id) if updated_address_id else None}
