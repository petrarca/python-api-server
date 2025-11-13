"""Tests for the model converter utility functions."""

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from api_server.utils.model_converter import to_response_model


# Define test SQLModel models (database models)
class MockAddressModel(SQLModel):
    """Test address model for database."""

    id: UUID = Field(default_factory=uuid4)
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"
    patient_id: UUID


class MockPatientModel(SQLModel):
    """Test patient model for database."""

    id: UUID = Field(default_factory=uuid4)
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    email: str | None = None
    phone: str | None = None
    patient_id: str
    # Use JSON type instead of ARRAY for SQLite compatibility
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    # Add addresses as a regular attribute, not a relationship
    addresses: list[MockAddressModel] = Field(default_factory=list)


class MockSpecialtyModel(SQLModel):
    """Test specialty model for database."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str


class MockDoctorModel(SQLModel):
    """Test doctor model for database."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    specialty_id: UUID
    specialty: MockSpecialtyModel | None = None


class MockDoctorResponse(BaseModel):
    """Test doctor response model for API."""

    id: UUID
    name: str
    specialty_id: UUID


class MockSpecialtyResponse(BaseModel):
    """Test specialty response model for API."""

    id: UUID
    name: str
    description: str


class MockDoctorWithSpecialtyResponse(MockDoctorResponse):
    """Test doctor response with specialty."""

    specialty: MockSpecialtyResponse


class MockMedicalRecordModel(SQLModel):
    """Test medical record model for database."""

    id: UUID = Field(default_factory=uuid4)
    record_type: str
    description: str
    patient_id: UUID
    doctor_id: UUID
    doctor: MockDoctorModel | None = None


class MockMedicalRecordResponse(BaseModel):
    """Test medical record response model for API."""

    id: UUID
    record_type: str
    description: str
    patient_id: UUID
    doctor_id: UUID


class MockMedicalRecordWithDoctorResponse(MockMedicalRecordResponse):
    """Test medical record response with doctor."""

    doctor: MockDoctorWithSpecialtyResponse


class MockAddressResponse(BaseModel):
    """Test address response model for API."""

    id: UUID
    street: str
    city: str
    state: str
    zip_code: str
    country: str


class MockPatientResponse(BaseModel):
    """Test patient response model for API."""

    id: UUID
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    email: str | None = None
    phone: str | None = None
    patient_id: str


class MockPatientWithAddressesResponse(MockPatientResponse):
    """Test patient response model with addresses for API."""

    addresses: list[MockAddressResponse] = []


@pytest.fixture
def sample_patient():
    """Create a sample patient with addresses for testing."""
    # Create a patient
    patient = MockPatientModel(
        first_name="John",
        last_name="Doe",
        date_of_birth="1980-01-01",
        gender="male",
        email="john.doe@example.com",
        phone="555-123-4567",
        patient_id="P12345",
    )

    # Create addresses
    address1 = MockAddressModel(
        id=uuid4(), street="123 Main St", city="Anytown", state="CA", zip_code="12345", country="US", patient_id=patient.id
    )

    address2 = MockAddressModel(
        id=uuid4(), street="456 Oak Ave", city="Somewhere", state="NY", zip_code="67890", country="US", patient_id=patient.id
    )

    # Add addresses to patient
    patient.addresses = [address1, address2]

    return patient


@pytest.fixture
def sample_medical_record():
    """Create a sample medical record with doctor and specialty for testing."""
    # Create a specialty
    specialty = MockSpecialtyModel(name="Cardiology", description="Heart specialist")

    # Create a doctor with the specialty
    doctor = MockDoctorModel(name="Dr. Smith", specialty_id=specialty.id)
    doctor.specialty = specialty

    # Create a medical record with the doctor
    record = MockMedicalRecordModel(
        record_type="Examination", description="Annual checkup", patient_id=uuid4(), doctor_id=doctor.id
    )
    record.doctor = doctor

    return record


def test_to_response_model_basic():
    """Test basic conversion without nested objects."""
    # Create a simple patient model
    patient = MockPatientModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Smith",
        date_of_birth="1985-05-15",
        gender="female",
        email="jane.smith@example.com",
        phone="555-987-6543",
        patient_id="P67890",
    )

    # Convert to response model
    response = to_response_model(patient, MockPatientResponse)

    # Check that the response is the correct type
    assert isinstance(response, MockPatientResponse)

    # Check that all fields were correctly copied
    assert response.id == patient.id
    assert response.first_name == patient.first_name
    assert response.last_name == patient.last_name
    assert response.date_of_birth == patient.date_of_birth
    assert response.gender == patient.gender
    assert response.email == patient.email
    assert response.phone == patient.phone
    assert response.patient_id == patient.patient_id


def test_to_response_model_with_nested_objects(sample_patient):
    """Test conversion with nested objects (addresses)."""
    # Convert to response model with addresses
    response = to_response_model(sample_patient, MockPatientWithAddressesResponse)

    # Verify patient data
    assert response is not None
    assert isinstance(response, MockPatientWithAddressesResponse)
    assert response.id == sample_patient.id
    assert response.first_name == sample_patient.first_name
    assert response.last_name == sample_patient.last_name

    # Verify addresses
    assert len(response.addresses) == 2
    assert all(isinstance(addr, MockAddressResponse) for addr in response.addresses)

    # Verify first address
    assert response.addresses[0].street == sample_patient.addresses[0].street
    assert response.addresses[0].city == sample_patient.addresses[0].city
    assert response.addresses[0].state == sample_patient.addresses[0].state

    # Verify second address
    assert response.addresses[1].street == sample_patient.addresses[1].street
    assert response.addresses[1].city == sample_patient.addresses[1].city
    assert response.addresses[1].state == sample_patient.addresses[1].state


def test_to_response_model_with_explicit_mapping(sample_patient):
    """Test conversion with explicit mapping for nested objects."""
    # Convert to response model with explicit mapping for addresses
    response = to_response_model(
        sample_patient,
        MockPatientWithAddressesResponse,  # Using response model that has addresses field
        mapping={"addresses": MockAddressResponse},
    )

    # Verify patient data
    assert response is not None
    assert isinstance(response, MockPatientWithAddressesResponse)
    assert response.id == sample_patient.id
    assert response.first_name == sample_patient.first_name
    assert response.last_name == sample_patient.last_name

    # Verify addresses were mapped correctly
    assert hasattr(response, "addresses")
    assert len(response.addresses) == 2
    assert all(isinstance(addr, MockAddressResponse) for addr in response.addresses)

    # Verify address data
    assert response.addresses[0].street == sample_patient.addresses[0].street
    assert response.addresses[1].city == sample_patient.addresses[1].city


def test_to_response_model_with_nested_mapping(sample_medical_record):
    """Test conversion with nested attribute mapping."""
    # Convert to response model with nested mapping (doctor.specialty)
    response = to_response_model(
        sample_medical_record,
        MockMedicalRecordWithDoctorResponse,  # Using response model that has doctor field
        mapping={"doctor": MockDoctorWithSpecialtyResponse, "doctor.specialty": MockSpecialtyResponse},
    )

    # Verify medical record data
    assert response is not None
    assert isinstance(response, MockMedicalRecordWithDoctorResponse)
    assert response.id == sample_medical_record.id
    assert response.record_type == sample_medical_record.record_type

    # Verify doctor was mapped correctly
    assert hasattr(response, "doctor")
    assert isinstance(response.doctor, MockDoctorWithSpecialtyResponse)
    assert response.doctor.id == sample_medical_record.doctor.id
    assert response.doctor.name == sample_medical_record.doctor.name

    # Verify specialty was mapped via nested mapping
    assert hasattr(response.doctor, "specialty")
    assert isinstance(response.doctor.specialty, MockSpecialtyResponse)
    assert response.doctor.specialty.id == sample_medical_record.doctor.specialty.id
    assert response.doctor.specialty.name == sample_medical_record.doctor.specialty.name


def test_to_response_model_with_none():
    """Test conversion with None input."""
    response = to_response_model(None, MockPatientResponse)
    assert response is None


def test_to_response_model_with_empty_list(sample_patient):
    """Test conversion with empty list of nested objects."""
    # Remove all addresses
    sample_patient.addresses = []

    # Convert to response model
    response = to_response_model(sample_patient, MockPatientWithAddressesResponse)

    # Verify conversion
    assert response is not None
    assert isinstance(response, MockPatientWithAddressesResponse)
    assert len(response.addresses) == 0


def test_to_response_model_with_single_nested_object(sample_medical_record):
    """Test conversion with a single nested object (not in a list)."""
    # Convert to response model
    response = to_response_model(sample_medical_record, MockMedicalRecordWithDoctorResponse)

    # Verify conversion
    assert response is not None
    assert isinstance(response, MockMedicalRecordWithDoctorResponse)
    assert response.id == sample_medical_record.id
    assert response.record_type == sample_medical_record.record_type
    assert response.description == sample_medical_record.description

    # Verify nested doctor object
    assert response.doctor is not None
    assert isinstance(response.doctor, MockDoctorWithSpecialtyResponse)
    assert response.doctor.id == sample_medical_record.doctor.id
    assert response.doctor.name == sample_medical_record.doctor.name
