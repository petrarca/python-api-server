"""
Address API - CRUD operations for address management.

This module provides REST endpoints for managing addresses:
- CRUD operations: Create, read, update, delete addresses
- Patient relationships: Get addresses by patient

All endpoints delegate to AddressService for business logic.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from api_server.database import get_db_session
from api_server.models.api_model import (
    AddressCreateInput,
    AddressCreateResponse,
    AddressInput,
    AddressResponse,
)
from api_server.services.address_service import AddressService, get_address_service

router = APIRouter()


@router.get("/addresses/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: UUID,
    address_service: AddressService = Depends(get_address_service),
    session: Session = Depends(get_db_session),
) -> AddressResponse:
    """Get an address by ID.

    Args:
        address_id: UUID of the address to retrieve
        address_service: Address service instance
        session: Database session

    Returns:
        AddressResponse object

    Raises:
        HTTPException: If address not found
    """
    address = address_service.get_address_by_id(session, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address with ID {address_id} not found",
        )
    return address


@router.get("/addresses/by-patient/{patient_id}", response_model=list[AddressResponse])
def get_addresses_by_patient(
    patient_id: UUID,
    address_service: AddressService = Depends(get_address_service),
    session: Session = Depends(get_db_session),
) -> list[AddressResponse]:
    """Get all addresses for a patient.

    Args:
        patient_id: UUID of the patient
        address_service: Address service instance
        session: Database session

    Returns:
        List of AddressResponse objects
    """
    return address_service.get_addresses_by_patient(session, patient_id)


@router.post("/addresses", response_model=AddressCreateResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address: AddressCreateInput,
    address_service: AddressService = Depends(get_address_service),
    session: Session = Depends(get_db_session),
) -> AddressCreateResponse:
    """Create a new address.

    Args:
        address: AddressCreateInput object containing address information
        address_service: Address service instance
        session: Database session

    Returns:
        AddressCreateResponse object

    Raises:
        HTTPException: If creation failed
    """
    created_address = address_service.create_address(session, address)
    if not created_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create address",
        )
    return created_address


@router.put("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: UUID,
    address: AddressInput,
    address_service: AddressService = Depends(get_address_service),
    session: Session = Depends(get_db_session),
) -> AddressResponse:
    """Update an address.

    Args:
        address_id: UUID of the address to update
        address: AddressInput object containing updated address information
        address_service: Address service instance
        session: Database session

    Returns:
        AddressResponse object

    Raises:
        HTTPException: If address not found or update failed
    """
    updated_address = address_service.update_address(session, address_id, address)
    if not updated_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address with ID {address_id} not found or update failed",
        )
    return updated_address


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: UUID,
    address_service: AddressService = Depends(get_address_service),
    session: Session = Depends(get_db_session),
) -> None:
    """Delete an address by ID.

    Args:
        address_id: UUID of the address to delete
        address_service: Address service instance
        session: Database session

    Raises:
        HTTPException: If address not found or deletion failed
    """
    success = address_service.delete_address(session, address_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address with ID {address_id} not found or deletion failed",
        )
