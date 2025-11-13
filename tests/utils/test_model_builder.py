"""Tests for the model builder utility functions."""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from api_server.utils.model_builder import ModelBuilder, create_model, create_model_builder


# Define test models
class SampleBaseModel(BaseModel):
    """Base model for testing."""

    id: str
    name: str
    email: str
    age: int
    is_active: bool = True
    tags: list[str] = []
    metadata: dict[str, Any] | None = None


class TestModelBuilder:
    """Tests for the ModelBuilder class."""

    def test_include_fields(self):
        """Test including specific fields."""
        model = ModelBuilder(SampleBaseModel).with_name("TestIncludeModel").include(["id", "name", "email"]).build()

        # Check model has correct fields
        assert "id" in model.model_fields
        assert "name" in model.model_fields
        assert "email" in model.model_fields

        # Check excluded fields are not in the model
        assert "age" not in model.model_fields
        assert "is_active" not in model.model_fields
        assert "tags" not in model.model_fields
        assert "metadata" not in model.model_fields

        # Create an instance to verify it works with included fields
        instance = model(id="123", name="Test", email="test@example.com")
        assert instance.id == "123"
        assert instance.name == "Test"
        assert instance.email == "test@example.com"

        # Verify we can't create an instance without required included fields
        with pytest.raises(ValidationError):
            model(id="123", name="Test")  # Missing email

    def test_exclude_fields(self):
        """Test excluding specific fields."""
        model = (
            ModelBuilder(SampleBaseModel).with_name("TestExcludeModel").exclude(["age", "is_active", "tags", "metadata"]).build()
        )

        # Check model has correct fields
        assert "id" in model.model_fields
        assert "name" in model.model_fields
        assert "email" in model.model_fields

        # Check excluded fields are not in the model
        assert "age" not in model.model_fields
        assert "is_active" not in model.model_fields
        assert "tags" not in model.model_fields
        assert "metadata" not in model.model_fields

        # Check model has correct required fields
        instance = model(id="123", name="Test", email="test@example.com")
        assert instance.id == "123"
        assert instance.name == "Test"
        assert instance.email == "test@example.com"

    def test_with_config(self):
        """Test setting model configuration."""
        model = ModelBuilder(SampleBaseModel).with_name("TestConfigModel").with_config({"extra": "forbid"}).build()

        # Check model configuration
        assert model.model_config["extra"] == "forbid"

        # In Pydantic v2, we can verify the model config is applied correctly
        # by checking the model_config directly
        assert model.model_config.get("extra") == "forbid"

        # For a more robust test, we can verify that the model actually
        # validates correctly with the expected fields
        instance = model(
            id="123",
            name="Test",
            email="test@example.com",
            age=30,
            is_active=True,
        )
        assert instance.id == "123"
        assert instance.name == "Test"
        assert instance.email == "test@example.com"
        assert instance.age == 30
        assert instance.is_active is True

    def test_override_field(self):
        """Test overriding field types and defaults."""
        model = (
            ModelBuilder(SampleBaseModel)
            .with_name("TestOverrideModel")
            .override_field("email", str, "default@example.com")
            .override_field("age", float, 25.5)
            .build()
        )

        # Check field types and defaults
        assert model.model_fields["email"].default == "default@example.com"
        assert model.model_fields["age"].annotation is float

        # Create an instance with defaults
        instance = model(id="123", name="Test")
        assert instance.email == "default@example.com"
        assert pytest.approx(25.5) == instance.age

        # Create an instance with custom values
        instance = model(id="123", name="Test", email="custom@example.com", age=30.5)
        assert instance.email == "custom@example.com"
        assert pytest.approx(30.5) == instance.age

    def test_with_all_fields(self):
        """Test setting all_fields parameter."""
        # Test with all_fields=True (default)
        model_all = ModelBuilder(SampleBaseModel).with_name("TestAllFieldsModel").build()

        # Check all fields are included
        assert "id" in model_all.model_fields
        assert "name" in model_all.model_fields
        assert "email" in model_all.model_fields
        assert "age" in model_all.model_fields
        assert "is_active" in model_all.model_fields
        assert "tags" in model_all.model_fields
        assert "metadata" in model_all.model_fields

        # Test with all_fields=False
        model_none = (
            ModelBuilder(SampleBaseModel)
            .with_name("TestNoFieldsModel")
            .with_all_fields(False)
            .override_field("custom_field", str, "custom")
            .build()
        )

        # Check no fields from base model are included
        assert "id" not in model_none.model_fields
        assert "name" not in model_none.model_fields
        assert "email" not in model_none.model_fields
        assert "age" not in model_none.model_fields
        assert "is_active" not in model_none.model_fields
        assert "tags" not in model_none.model_fields
        assert "metadata" not in model_none.model_fields

        # Check overridden field is included
        assert "custom_field" in model_none.model_fields
        assert model_none.model_fields["custom_field"].default == "custom"

    def test_build_without_name(self):
        """Test that building without a name raises an error."""
        builder = ModelBuilder(SampleBaseModel)
        with pytest.raises(ValueError, match="Model name must be set"):
            builder.build()


class TestCreateModelFunction:
    """Tests for the create_model function."""

    def test_create_model_with_fields(self):
        """Test creating a model with included fields."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestIncludeModel",
            fields=["id", "name", "email"],
        )

        # Check model has the required fields
        assert "id" in model.model_fields
        assert "name" in model.model_fields
        assert "email" in model.model_fields

        # Check excluded fields are not in the model
        assert "age" not in model.model_fields
        assert "is_active" not in model.model_fields
        assert "tags" not in model.model_fields
        assert "metadata" not in model.model_fields

        # Create an instance with required fields
        instance = model(id="123", name="Test", email="test@example.com")
        assert instance.id == "123"
        assert instance.name == "Test"
        assert instance.email == "test@example.com"

        # Verify we can't create an instance without required included fields
        with pytest.raises(ValidationError):
            model(id="123", name="Test")  # Missing email

    def test_create_model_with_excluded_fields(self):
        """Test creating a model with excluded fields."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestExcludeModel",
            excluded_fields=["age", "is_active"],
        )

        # Check model has correct fields
        assert "id" in model.model_fields
        assert "name" in model.model_fields
        assert "email" in model.model_fields

        # Check excluded fields are not in the model
        assert "age" not in model.model_fields
        assert "is_active" not in model.model_fields

        # Check we can create an instance without the excluded fields
        instance = model(id="123", name="Test", email="test@example.com")
        assert instance.id == "123"
        assert instance.name == "Test"
        assert instance.email == "test@example.com"

    def test_create_model_with_config(self):
        """Test creating a model with configuration."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestConfigModel",
            config={"extra": "forbid"},
        )

        # Check model configuration
        assert model.model_config["extra"] == "forbid"

    def test_create_model_with_field_overrides_dict(self):
        """Test creating a model with field overrides dictionary."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestOverrideModel",
            field_overrides={
                "email": (str, "default@example.com"),
                "age": (float, 25.5),
            },
        )

        # Check field types and defaults
        assert model.model_fields["email"].default == "default@example.com"
        assert model.model_fields["age"].annotation is float

    def test_create_model_with_field_override_kwargs(self):
        """Test creating a model with field overrides as keyword arguments."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestOverrideKwargsModel",
            email=(str, "default@example.com"),
            age=(float, 25.5),
        )

        # Check field types and defaults
        assert model.model_fields["email"].default == "default@example.com"
        assert model.model_fields["age"].annotation is float

    def test_create_model_with_all_fields_parameter(self):
        """Test creating a model with the all_fields parameter."""
        # Test with all_fields=True (default)
        model_all = create_model(
            base_model=SampleBaseModel,
            name="TestAllFieldsModel",
        )

        # Check all fields are included
        assert "id" in model_all.model_fields
        assert "name" in model_all.model_fields
        assert "email" in model_all.model_fields
        assert "age" in model_all.model_fields
        assert "is_active" in model_all.model_fields

        # Test with all_fields=False
        model_none = create_model(
            base_model=SampleBaseModel,
            name="TestNoFieldsModel",
            all_fields=False,
            custom_field=(str, "custom"),
        )

        # Check no fields from base model are included
        assert "id" not in model_none.model_fields
        assert "name" not in model_none.model_fields
        assert "email" not in model_none.model_fields
        assert "age" not in model_none.model_fields
        assert "is_active" not in model_none.model_fields

        # Check overridden field is included
        assert "custom_field" in model_none.model_fields
        assert model_none.model_fields["custom_field"].default == "custom"

        # Test that fields parameter takes precedence over all_fields
        model_fields = create_model(
            base_model=SampleBaseModel,
            name="TestFieldsOverAllModel",
            fields=["id", "name"],
            all_fields=False,  # This should be ignored when fields is specified
        )

        # Check only specified fields are included
        assert "id" in model_fields.model_fields
        assert "name" in model_fields.model_fields
        assert "email" not in model_fields.model_fields
        assert "age" not in model_fields.model_fields

    def test_create_model_with_all_options(self):
        """Test creating a model with all options."""
        model = create_model(
            base_model=SampleBaseModel,
            name="TestAllOptionsModel",
            fields=["id", "name", "email"],
            config={"extra": "forbid"},
            field_overrides={"email": (str, "default@example.com")},
            age=(float, 25.5),
        )

        # Check model has the included fields
        assert "id" in model.model_fields
        assert "name" in model.model_fields
        assert "email" in model.model_fields

        # Check model has the overridden fields but not other fields
        assert "age" in model.model_fields
        assert "is_active" not in model.model_fields
        assert "tags" not in model.model_fields
        assert "metadata" not in model.model_fields

        # Check field types and defaults
        assert model.model_fields["email"].default == "default@example.com"
        assert model.model_fields["age"].annotation is float
        assert pytest.approx(25.5) == model.model_fields["age"].default

        # Check model configuration
        assert model.model_config["extra"] == "forbid"

    def test_create_model_with_api_model_parameter(self):
        """Test creating a model with the api_model parameter."""
        # Test with api_model=True
        model_api = create_model(
            base_model=SampleBaseModel,
            name="TestApiModel",
            api_model=True,
        )

        # Check that extra=forbid is set in the model config
        assert model_api.model_config["extra"] == "forbid"

        # Test with api_model=True but explicit config overrides it
        model_api_override = create_model(
            base_model=SampleBaseModel,
            name="TestApiModelOverride",
            api_model=True,
            config={"extra": "ignore"},
        )

        # Check that the explicit config takes precedence
        assert model_api_override.model_config["extra"] == "ignore"

        # Test with api_model=False (default)
        model_non_api = create_model(
            base_model=SampleBaseModel,
            name="TestNonApiModel",
        )

        # Check that extra is not set to forbid in the model config
        assert model_non_api.model_config.get("extra") != "forbid"


class TestCreateModelBuilder:
    """Tests for the create_model_builder function."""

    def test_create_model_builder(self):
        """Test that create_model_builder returns a ModelBuilder instance."""
        builder = create_model_builder(SampleBaseModel)
        assert isinstance(builder, ModelBuilder)
        assert builder.base_model == SampleBaseModel
