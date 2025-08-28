"""Model builder utilities for creating Pydantic models dynamically."""

from typing import Any

from pydantic import BaseModel
from pydantic import create_model as pydantic_create_model


class ModelBuilder:
    """Builder class for creating models with a fluent API."""

    def __init__(self, base_model: type[BaseModel]):
        """Initialize the builder with a base model.

        Args:
            base_model: The base model to inherit from
        """
        self.base_model = base_model
        self.model_name = None
        self.included_fields = None
        self.excluded_fields = None
        self.model_config = None
        self.field_overrides = {}
        self.all_fields = True
        self.api_model = False

    def with_name(self, name: str) -> "ModelBuilder":
        """Set the name for the model.

        Args:
            name: Name for the new model

        Returns:
            Self for method chaining
        """
        self.model_name = name
        return self

    def include(self, fields: list[str]) -> "ModelBuilder":
        """Include only specified fields from the base model.

        Args:
            fields: List of field names to include

        Returns:
            Self for method chaining
        """
        self.included_fields = fields
        self.excluded_fields = None
        return self

    def exclude(self, fields: list[str]) -> "ModelBuilder":
        """Exclude specified fields from the base model.

        Args:
            fields: List of field names to exclude

        Returns:
            Self for method chaining
        """
        self.excluded_fields = fields
        self.included_fields = None
        return self

    def with_config(self, config: dict[str, Any]) -> "ModelBuilder":
        """Set model configuration.

        Args:
            config: Dictionary with model configuration

        Returns:
            Self for method chaining
        """
        self.model_config = config
        return self

    def with_all_fields(self, all_fields: bool) -> "ModelBuilder":
        """Set whether to include all fields from the base model.

        Only relevant if neither include nor exclude is specified.

        Args:
            all_fields: Whether to include all fields from the base model

        Returns:
            Self for method chaining
        """
        self.all_fields = all_fields
        return self

    def with_api_model(self, api_model: bool) -> "ModelBuilder":
        """Set whether this is an API model.

        If true, will add {"extra": "forbid"} to the model config
        unless explicitly overridden by with_config.

        Args:
            api_model: Whether this is an API model

        Returns:
            Self for method chaining
        """
        self.api_model = api_model
        return self

    def override_field(self, field_name: str, annotation: Any, default: Any = ...) -> "ModelBuilder":
        """Override a field's type and default value.

        Args:
            field_name: Name of the field to override
            annotation: Type annotation for the field
            default: Default value for the field

        Returns:
            Self for method chaining
        """
        self.field_overrides[field_name] = (annotation, default)
        return self

    def _get_field_default(self, field_info) -> Any:
        """Extract the default value from a field.

        Args:
            field_info: Field information from the model

        Returns:
            Default value or ... if no default
        """
        return field_info.default if field_info.default is not ... else ...

    def _get_included_fields(self) -> dict[str, tuple[Any, Any]]:
        """Get fields to include based on include/exclude settings.

        Returns:
            Dictionary of field definitions
        """
        fields = {}

        def add_field(field_name: str) -> None:
            """Helper function to process a field and add it to the fields dictionary."""
            if field_name in self.base_model.model_fields:
                field_info = self.base_model.model_fields[field_name]
                default = self._get_field_default(field_info)
                fields[field_name] = (field_info.annotation, default)

        if self.included_fields is not None:
            # Case 1: Only include specified fields
            for field in self.included_fields:
                add_field(field)
        elif self.excluded_fields is not None:
            # Case 2: Include all fields except those explicitly excluded
            for field in self.base_model.model_fields:
                if field not in self.excluded_fields:
                    add_field(field)
        elif self.all_fields:
            # Case 3: Include all fields
            for field in self.base_model.model_fields:
                add_field(field)

        return fields

    def _create_model(self, fields: dict[str, tuple[Any, Any]]) -> type[BaseModel]:
        """Create a Pydantic model with the given fields.

        Args:
            fields: Dictionary of field definitions

        Returns:
            New Pydantic model
        """
        model_config = self.model_config or {}
        if self.api_model and "extra" not in model_config:
            model_config["extra"] = "forbid"
        model = pydantic_create_model(self.model_name, __module__=__name__, **fields)
        model.model_config.update(model_config)
        return model

    def build(self) -> type[BaseModel]:
        """Build and return the model.

        Returns:
            A new Pydantic model with the selected fields

        Raises:
            ValueError: If model_name is not set
        """
        if not self.model_name:
            raise ValueError("Model name must be set using with_name() before building")
        fields = self._get_included_fields()
        fields.update(self.field_overrides)
        return self._create_model(fields)


def create_model_builder(base_model: type[BaseModel]) -> ModelBuilder:
    """Create a model builder for the given base model.

    Args:
        base_model: The base model to inherit from

    Returns:
        A ModelBuilder instance for fluent API usage
    """
    return ModelBuilder(base_model)


def create_model(
    base_model: type[BaseModel],
    name: str,
    fields: list[str] | None = None,
    excluded_fields: list[str] | None = None,
    config: dict[str, Any] | None = None,
    field_overrides: dict[str, tuple[Any, Any]] | None = None,
    all_fields: bool = True,
    api_model: bool = False,
    **field_override_kwargs: Any,
) -> type[BaseModel]:
    """Create a model based on a base model with various customizations.

    This is a unified function that can handle all model creation cases:
    - Create a model with only specified fields (include)
    - Create a model excluding specified fields (exclude)
    - Create a complete model with all fields

    Args:
        base_model: The base model to inherit from
        name: Name for the new model
        fields: Optional list of field names to include (takes precedence over excluded_fields)
        excluded_fields: Optional list of field names to exclude (only used if fields is None)
        config: Optional model configuration
        field_overrides: Optional field overrides as {field_name: (annotation, default)}
        all_fields: Whether to include all fields from the base model (only used if fields and excluded_fields are None)
        api_model: Whether this is an API model (if true, adds {"extra": "forbid"} to config unless explicitly overridden)
        **field_override_kwargs: Direct field overrides as keyword arguments
            Format: field_name=(annotation, default)

    Returns:
        A new Pydantic model with the selected fields

    Examples:
        # Create a model with only specific fields
        PatientResponse = create_model(
            PatientBase,
            "PatientResponse",
            fields=["id", "patient_id", "email"],
            email=(str, ...),
            first_name=(str, Field(default="Unknown"))
        )

        # Create a model excluding specific fields
        PatientResponseExclude = create_model(
            PatientBase,
            "PatientResponseExclude",
            excluded_fields=["conditions", "allergies"]
        )

        # Create a model with all fields
        PatientResponseAll = create_model(
            PatientBase,
            "PatientResponseAll",
            config={"extra": "forbid"},
            email=(str, ...)
        )

        # Create an empty model (no fields from base model)
        PatientResponseEmpty = create_model(
            PatientBase,
            "PatientResponseEmpty",
            all_fields=False,
            email=(str, ...)  # Only add the email field
        )

        # Create an API model with extra fields forbidden
        PatientApiModel = create_model(
            PatientBase,
            "PatientApiModel",
            api_model=True,
            # This will automatically add {"extra": "forbid"} to config
        )
    """
    builder = create_model_builder(base_model).with_name(name).with_all_fields(all_fields)
    if fields is not None:
        builder = builder.include(fields)
    elif excluded_fields is not None:
        builder = builder.exclude(excluded_fields)
    if config:
        builder = builder.with_config(config)
    if field_overrides:
        for field_name, (annotation, default) in field_overrides.items():
            builder = builder.override_field(field_name, annotation, default)
    for field_name, override in field_override_kwargs.items():
        if isinstance(override, tuple) and len(override) == 2:
            annotation, default = override
            builder = builder.override_field(field_name, annotation, default)
    builder = builder.with_api_model(api_model)
    return builder.build()
