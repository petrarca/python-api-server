# Agent Instructions

This file contains rules and conventions for AI coding assistants working on this API server project.

## Service Layer Patterns

### Singleton Service Pattern

**All service classes must follow the standard singleton pattern using `@lru_cache`.**

#### Required Implementation:

```python
from functools import lru_cache

class YourService:
    """Service description."""
    
    def __init__(self):
        self.dependency = get_dependency_service()

@lru_cache
def get_your_service() -> YourService:
    """Get or create the singleton YourService instance.

    Returns:
        The YourService instance.
    """
    return YourService()
```

#### Requirements:

1. **Use `@lru_cache` decorator** on the getter function
2. **Function returns service instance** (not the class)
3. **Standard docstring with "singleton"**
4. **No global variables** for service instances
5. **Initialize dependencies in `__init__`** using their getter functions

#### Examples in this codebase:

- `HealthCheckService` - `get_health_check_service()`
- `PatientService` - `get_patient_service()`
- `AddressService` - `get_address_service()`

## Logging

### Use loguru's `{}` placeholder format

**Use loguru's `{}` placeholder format instead of f-strings for all logging calls** (e.g., `logger.debug("Processing {}", value)` not `logger.debug(f"Processing {value}")`).

This is loguru's native format and provides lazy evaluation — the string is only formatted if the message will actually be emitted. With f-strings, Python evaluates the string before the logging call, wasting CPU when the log level is disabled.

#### Good:
```python
logger.info("User {} logged in from {}", username, ip_address)
logger.error("Failed to process request: {}", error)
```

#### Bad:
```python
logger.info(f"User {username} logged in from {ip_address}")
logger.error(f"Failed to process request: {error}")
```

## Error Handling Patterns

### Specific Exception Handling

**Avoid catching broad `Exception` - use specific exception types.**

#### Good:
```python
try:
    service.create_resource(session, input_data)
except (ResourceNotFoundError, VersionConflictError, ValueError, RuntimeError) as e:
    logger.warning("Failed to create resource: {}", e)
    return False
```

#### Bad:
```python
try:
    service.create_resource(session, input_data)
except Exception as e:  # Too broad
    logger.warning(f"Failed to create resource: {e}")
    return False
```

#### Common Exception Types:

- **Application**: `ResourceNotFoundError`, `VersionConflictError` (from `exceptions.py`)
- **Validation**: `ValueError`, `TypeError`
- **Runtime**: `RuntimeError`, `AttributeError`
- **Database**: `SQLAlchemyError`

## Service Dependencies

### Dependency Injection Pattern

**Services should declare dependencies in `__init__` and use getter functions.**

```python
class YourService:
    def __init__(self):
        self.health_service = get_health_check_service()
        self.patient_service = get_patient_service()
```

### DI Registration Pattern

**Core services must be registered in `services/di.py` using getter functions.**

```python
def register_core_services(registry: ServiceRegistry) -> None:
    registry.register_factory(YourService, get_your_service)
```

### Service Usage Pattern

**Use `get_*_service()` in services and checks:**
```python
class YourService:
    def __init__(self):
        self.patient_service = get_patient_service()
```

**Use `registry.get()` in FastAPI/GraphQL contexts:**
```python
# API endpoints, GraphQL resolvers
def some_endpoint(registry: ServiceRegistry = Depends(get_service_registry)):
    service = registry.get(YourService)
```

## Date/Time Patterns

### Timezone-Aware Datetime Usage

**Always use arrow.py for date/time operations.**

#### Required Implementation:

```python
import arrow

# Use arrow for all datetime operations
current_time = arrow.utcnow().datetime
created_at = arrow.utcnow()
formatted = arrow.get(created_at).format('YYYY-MM-DD HH:mm:ss')
```

#### Requirements:

1. **Use `arrow.utcnow().datetime`** for all timestamp creation
2. **Use arrow for date/time arithmetic** (shifting, formatting, parsing)
3. **Always store UTC** in database, convert to local time only for display
4. **Use ISO format** for API responses when possible

#### Bad (deprecated):
```python
from datetime import datetime
user.created_at = datetime.utcnow()  # Deprecated since Python 3.12!
```

## Model Architecture Approach

### Three-Layer Model Separation

**Clean separation between database schema and API contracts using three model layers:**

#### **1. Base Models (`base_model.py`)**
- **Purpose**: Shared fields and common functionality
- **Usage**: Inherited by database models and API models
- **Contains**: Audit fields, common constraints, shared validation
- **Example**: `PatientBase` with `patient_id`, `first_name`, `last_name`

#### **2. Database Models (`db_model.py`)**
- **Purpose**: Database table definitions with SQLModel
- **Usage**: Database operations, migrations, ORM queries
- **Contains**: Primary keys, foreign keys, indexes, table-specific fields
- **Example**: `class Patient(PatientBase, table=True)` with `id: UUID = Field(primary_key=True)`

#### **3. API Models (`api_model.py`)**
- **Purpose**: Request/response validation and serialization
- **Usage**: FastAPI endpoints, API documentation, client contracts
- **Contains**: Input validation, response formatting, API-specific fields
- **Examples**: 
  - `PatientCreateInput` - POST request body
  - `PatientResponse` - GET response body  
  - `PatientInput` - PUT request body

### Benefits of This Approach
- **Separation of Concerns**: Database schema != API contract
- **Security**: API models expose only necessary fields
- **Flexibility**: Can evolve API independently of database
- **Validation**: Different validation rules for different contexts
- **Documentation**: Auto-generated OpenAPI specs from API models

### Model Implementation

**Follow the established patterns in these modules:**
- `models/base_model.py` - Base model definitions
- `models/db_model.py` - Database table models  
- `models/api_model.py` - API models using `create_model` utility
- `utils/model_builder.py` - `create_model` implementation

**Use `create_model` utility for API models to ensure consistency and maintain DRY principles.**

## CLI Architecture

### Dual Entry Points

The server provides two CLI entry points:

1. **`api-server`** - Main server with subcommands:
   - `api-server` (default: starts server)
   - `api-server run` (explicit: starts server)
   - `api-server check` (readiness checks only)
   - `api-server cli db check` (admin CLI as subgroup)

2. **`api-server-cli`** - Standalone admin CLI:
   - `api-server-cli db check`
   - `api-server-cli db upgrade`

### Adding New CLI Commands

1. Create a new file in `cli/commands/` with a `typer.Typer()` app
2. Register it in `cli/app.py` with `app.add_typer()`
3. Export it in `cli/commands/__init__.py`

### CLI Pipeline Builders

CLI operations use their own pipeline builders (in `cli/checks/pipeline_builders.py`)
separate from the server's pipeline builders. This allows CLI-specific check combinations
(e.g., basic checks before migration, full checks after).

## Readiness Pipeline

### Check Implementation

New readiness checks should extend `ReadinessCheck`:

```python
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult

class YourCheck(ReadinessCheck):
    def __init__(self, name="your_check", is_critical=False, run_once=False):
        super().__init__(name, is_critical, run_once)
    
    def _execute(self) -> ReadinessCheckResult:
        # Perform check
        if success:
            return self.success("Check passed", {"detail": "value"})
        return self.failed("Check failed", {"error": "reason"})
```

### Pipeline Stage Constants

Use constants from `constants.py` for stage names:
```python
from api_server.constants import STAGE_DATABASE
```
