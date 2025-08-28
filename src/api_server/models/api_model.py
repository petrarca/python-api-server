"""API models for API server."""

from api_server.models.base_model import AddressBase, PatientBase
from api_server.utils.model_builder import create_model

# Patient API response model - create base version first
PatientResponseBase = create_model(base_model=PatientBase, name="PatientResponseBase", all_fields=True)


# Add the age computed field to PatientResponse
class PatientResponse(PatientResponseBase):
    # Include the age computed field from PatientBase
    age: int | None = None


# Address API response model
AddressResponse = create_model(base_model=AddressBase, name="AddressResponse", all_fields=True)


# Patient input model (excludes id field)
PatientInput = create_model(
    base_model=PatientBase,
    name="PatientInput",
    excluded_fields=["id"],
    api_model=True,
)


# Address input model (excludes id field)
AddressInput = create_model(
    base_model=AddressBase,
    name="AddressInput",
    excluded_fields=["id"],
    api_model=True,
)


# Patient create input (includes address)
class PatientCreateInput(PatientInput):
    addresses: list[AddressInput]


# Patient create response (includes address)
class PatientCreateResponse(PatientResponse):
    addresses: list[AddressResponse] = []
