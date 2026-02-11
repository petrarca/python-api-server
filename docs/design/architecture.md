# Architecture & Design

## Overview

This template provides a production-ready Python API server built on FastAPI. It is designed as a
foundation that can be extended for specific applications while providing robust defaults for
common concerns: health checking, database management, event handling, and CLI tooling.

## Core Patterns

### Three-Layer Model Architecture

Clean separation between database schema and API contracts:

| Layer | File | Purpose |
|-------|------|---------|
| **Base** | `models/base_model.py` | Shared fields, constraints, validation |
| **Database** | `models/db_model.py` | SQLModel table definitions, foreign keys, indexes |
| **API** | `models/api_model.py` | Request/response models, API-specific validation |

This allows the API contract to evolve independently of the database schema, and ensures
only intended fields are exposed to clients.

### Singleton Services with `@lru_cache`

All services follow a standard pattern:

```python
class YourService:
    def __init__(self):
        self.dependency = get_dependency_service()

@lru_cache
def get_your_service() -> YourService:
    return YourService()
```

Services are registered in `services/di.py` and accessed via the `ServiceRegistry` in
FastAPI/GraphQL contexts, or directly via `get_*_service()` in other services and checks.

### Dependency Injection

Two access patterns:

- **Services/checks**: Call `get_*_service()` directly (singleton via `@lru_cache`)
- **API/GraphQL**: Use `registry.get(ServiceType)` via FastAPI `Depends()`

Registration happens in `services/di.py` with `register_factory()` or `register_singleton()`.

## Readiness Pipeline

A stage-based health check system that runs during startup and on demand:

```
Pipeline
  └── Stage: "database" (critical=False, fail_fast=True)
        ├── DatabaseInitializationCheck
        ├── DatabaseHealthCheck
        └── DatabaseSchemaCheck
```

**Key concepts:**
- **Stages** group related checks and can be marked `is_critical` (stops pipeline on failure)
- **Checks** extend `ReadinessCheck` and implement `_execute()` returning success/failure
- **`run_once`** checks cache results; `force_rerun` parameter on the health endpoint re-executes them
- **Pipeline builders** in `checks/pipeline_builders.py` compose stages for the server
- **CLI pipeline builders** in `cli/checks/pipeline_builders.py` compose different check combinations for admin operations

### Adding a Check

```python
from api_server.readiness_pipeline import ReadinessCheck, ReadinessCheckResult

class MyCheck(ReadinessCheck):
    def __init__(self):
        super().__init__("my_check", is_critical=False, run_once=False)

    def _execute(self) -> ReadinessCheckResult:
        if everything_ok:
            return self.success("All good", {"detail": "value"})
        return self.failed("Problem", {"error": "reason"})
```

Register it in a pipeline builder by calling `builder.add_check(MyCheck())` within a stage.

## Event Bus

In-process async event system with dependency injection:

```python
# Define event
class OrderCreated(BaseEvent):
    order_id: str

# Register handler (function or class)
event_bus.register(OrderCreated, handle_order_created)

# Emit
await event_bus.emit(OrderCreated(order_id="123"))
```

Handlers receive the event and can declare service dependencies that are injected from the
`ServiceRegistry`.

## Database Layer

### Connection Management

`database/connection.py` provides:
- `init_db()` / `dispose_db()` -- lifecycle management
- `get_engine()` -- SQLAlchemy engine (singleton)
- `get_db_session()` -- FastAPI dependency (yields session)
- `borrow_db_session()` -- context manager for non-request code

### Advisory Locks

`database/advisory_lock.py` provides PostgreSQL advisory locks for distributed coordination:

```python
from api_server.database import advisory_lock, AdvisoryLock

with advisory_lock(AdvisoryLock.MIGRATION):
    # Only one process enters here across all instances
    perform_migration()
```

Also available as non-blocking `try_advisory_lock()` which yields `None` if the lock
is held by another process.

Used by `AlembicManager.perform_migration()` to prevent concurrent migration attempts
in multi-instance deployments.

### Alembic Integration

`AlembicManager` wraps alembic operations with:
- Table existence check before querying `alembic_version` (safe on fresh databases)
- Advisory lock + double-checked locking on migrations
- Schema validation without performing migrations (`validate_schema_state()`)

## Exception Handling

`exceptions.py` defines generic server exceptions:

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `ResourceNotFoundError` | 404 | Resource lookup by ID/key fails |
| `VersionConflictError` | 409 | Optimistic locking version mismatch |

These are automatically mapped to HTTP responses by `exception_handlers.py` via
`register_exception_handlers(app)`.

## CLI Architecture

### Dual Entry Points

| Entry Point | Usage |
|-------------|-------|
| `api-server` | Main server; CLI accessible as `api-server cli db check` |
| `api-server-cli` | Standalone admin CLI: `api-server-cli db check` |

The main app uses `callback(invoke_without_command=True)` so running `api-server` without
a subcommand starts the server (default behavior).

### Adding CLI Commands

1. Create `cli/commands/yourcommand.py` with a `typer.Typer()` app
2. Register in `cli/app.py`: `app.add_typer(yourcommand.app, name="yourcommand")`
3. Export in `cli/commands/__init__.py`

CLI commands use their own pipeline builders (`cli/checks/pipeline_builders.py`) for
operation-specific check combinations (e.g., basic checks before migration, full checks after).

## Profiles

The `API_SERVER_PROFILES` setting controls which API surfaces are enabled:

| Profile | Effect |
|---------|--------|
| `rest` | REST endpoints only |
| `graphql` | GraphQL endpoint only |
| (empty/both) | All endpoints enabled |

Profiles are parsed at startup and available via `get_active_profiles()`.

## UUID and Timestamps

- **Primary keys**: UUID v7 (`_uuid7()`) for time-ordered, index-friendly IDs.
  Falls back to UUID v4 on Python < 3.14.
- **Timestamps**: `arrow.utcnow().datetime` via `_utcnow()`.
  Avoids the deprecated `datetime.utcnow()` (Python 3.12+).

## Logging

All logging routes through loguru via `InterceptHandler` which intercepts stdlib `logging`.

- Application log level controlled by `API_SERVER_LOG_LEVEL`
- SQLAlchemy logging separately configurable via `setup_sqlalchemy_logging()`
- Overly verbose third-party loggers (e.g., `watchfiles`) suppressed to WARNING
