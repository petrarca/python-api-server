"""Utility functions for converting between database and API models."""

from typing import Any, TypeVar, get_args, get_origin

from pydantic import BaseModel
from sqlmodel import SQLModel

# Define generic type variables
T = TypeVar("T", bound=SQLModel)  # Database model type
R = TypeVar("R", bound=BaseModel)  # API response model type


def _convert_to_dict(db_model: Any) -> dict:
    """Convert a model instance to a dictionary."""
    if db_model is None:
        return {}
    if isinstance(db_model, SQLModel):
        return db_model.model_dump()
    elif hasattr(db_model, "__dict__"):
        return {k: v for k, v in db_model.__dict__.items() if not k.startswith("_")}
    return {}


def _convert_collection(items: list | set | tuple, target_model: type[BaseModel]) -> list:
    """Convert a collection of items to a list of response models."""
    return [to_response_model(item, target_model).model_dump() for item in items if item is not None]


def _convert_single_item(item: Any, target_model: type[BaseModel]) -> dict:
    """Convert a single item to a response model."""
    if item is None:
        return {}
    return to_response_model(item, target_model).model_dump()


def _get_nested_attribute(obj: Any, attr_path: str) -> tuple[Any, str, Any]:
    """Get a nested attribute from an object.

    Returns:
        Tuple of (parent_object, final_attribute_name, attribute_value)
    """
    if not attr_path or obj is None:
        return None, "", None
    parts = attr_path.split(".")
    current_obj = obj
    # For simple attributes
    if len(parts) == 1:
        return obj, parts[0], getattr(obj, parts[0], None)
    # Navigate through the object hierarchy for nested attributes
    for part in parts[:-1]:
        if hasattr(current_obj, part):
            current_obj = getattr(current_obj, part)
            if current_obj is None:
                return None, parts[-1], None
        else:
            return None, parts[-1], None
    return current_obj, parts[-1], getattr(current_obj, parts[-1], None)


def _process_simple_mapping(db_model: Any, attr_name: str, target_model: type[BaseModel]) -> dict | None:
    """Process a simple (non-nested) attribute mapping."""
    if not hasattr(db_model, attr_name):
        return None
    value = getattr(db_model, attr_name)
    if value is None:
        return None
    if isinstance(value, list | set | tuple):
        return _convert_collection(value, target_model)
    return _convert_single_item(value, target_model)


def _process_nested_mapping(
    db_model: Any, response_model_class: type[BaseModel], attr_path: str, target_model: type[BaseModel]
) -> tuple[str, dict] | None:
    """Process a nested attribute mapping.

    Returns:
        Tuple of (parent_field_name, updated_parent_dict) or None if mapping can't be applied
    """
    parent_obj, final_attr, value = _get_nested_attribute(db_model, attr_path)
    if parent_obj is None or value is None:
        return None
    # Get the parent field name (first part of the path)
    parent_field = attr_path.split(".")[0]
    if parent_field not in response_model_class.model_fields:
        return None
    # Get the parent field type from the response model
    parent_field_type = response_model_class.model_fields[parent_field].annotation
    # Check if the parent field is a Pydantic model and has the nested attribute
    if not isinstance(parent_field_type, type) or not issubclass(parent_field_type, BaseModel) or final_attr not in parent_field_type.model_fields:
        return None
    # Get the parent value from the database model
    parent_value = getattr(db_model, parent_field)
    if parent_value is None:
        return None
    # Convert the parent to its response model
    parent_response = to_response_model(parent_value, parent_field_type)
    # Convert the nested value
    nested_value = to_response_model(value, target_model)
    # Update the parent model with the nested value
    parent_dict = parent_response.model_dump()
    parent_dict[final_attr] = nested_value.model_dump()
    return parent_field, parent_dict


def _process_explicit_mappings(db_model: Any, response_model_class: type[BaseModel], mapping: dict[str, type[BaseModel]]) -> dict:
    """Process explicit mappings for attributes."""
    result = {}
    for attr_path, target_model in mapping.items():
        # Skip mappings for attributes that don't exist in the response model
        if attr_path not in response_model_class.model_fields:
            continue
        # Handle simple attribute paths
        if "." not in attr_path:
            converted = _process_simple_mapping(db_model, attr_path, target_model)
            if converted is not None:
                result[attr_path] = converted
        else:
            # Handle nested attribute paths
            nested_result = _process_nested_mapping(db_model, response_model_class, attr_path, target_model)
            if nested_result:
                parent_field, parent_dict = nested_result
                result[parent_field] = parent_dict
    return result


def _process_nested_models(db_model: Any, response_model_class: type[BaseModel]) -> dict:
    """Process nested models based on response model field types."""
    result = {}
    for field_name, field_info in response_model_class.model_fields.items():
        field_type = field_info.annotation
        # Skip if the db_model doesn't have this field or it's None
        if not hasattr(db_model, field_name) or getattr(db_model, field_name) is None:
            continue
        value = getattr(db_model, field_name)
        # Handle single nested model
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            if isinstance(value, list | set | tuple):
                result[field_name] = _convert_collection(value, field_type)
            else:
                result[field_name] = _convert_single_item(value, field_type)
        # Handle list of nested models
        elif (
            get_origin(field_type) is list
            and len(get_args(field_type)) > 0
            and isinstance(get_args(field_type)[0], type)
            and issubclass(get_args(field_type)[0], BaseModel)
        ):
            item_type = get_args(field_type)[0]
            result[field_name] = _convert_collection(value, item_type)
    return result


def to_response_model[T: SQLModel, R: BaseModel](db_model: T, response_model_class: type[R], mapping: dict[str, type[BaseModel]] | None = None) -> R:
    """Convert a database model to an API response model.

    This function handles nested objects and lists by recursively converting them
    to the appropriate response model types. You can also specify explicit mappings
    for nested objects.

    Args:
        db_model: The database model instance to convert
        response_model_class: The API response model class to convert to
        mapping: Optional dictionary mapping attribute paths to response model classes.
                Example: {"addresses": AddressResponse, "doctor.specialty": SpecialtyResponse}
                Note: Mapped attributes must exist in the response model class.

    Returns:
        An instance of the API response model
    """
    if db_model is None:
        return None
    # Convert the database model to a dictionary
    model_dict = _convert_to_dict(db_model)
    # Process explicit mappings if provided
    if mapping:
        mapped_fields = _process_explicit_mappings(db_model, response_model_class, mapping)
        model_dict.update(mapped_fields)
    # Otherwise, check response model fields for nested objects
    else:
        nested_fields = _process_nested_models(db_model, response_model_class)
        model_dict.update(nested_fields)
    # Create the response model with model_validate
    return response_model_class.model_validate(model_dict)
