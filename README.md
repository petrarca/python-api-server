# Python API Server Template

A production-ready FastAPI template with REST & GraphQL endpoints, readiness pipeline, event bus, and modern tooling.

## Features

- **FastAPI** with REST endpoints and **Strawberry GraphQL**
- **Readiness Pipeline** - Modular health checks with stage-based execution
- **Internal Event Bus** - In-process async event handling with dependency injection
- **Sample Service & Event Handler** - Patient service and event handler examples
- **SQLModel**/SQLAlchemy with PostgreSQL and Alembic migrations
- **Modern Tooling** - uv package manager, ruff formatting/linting, pytest
- **Docker** - Multi-stage build for production deployment
- **Taskfile** - Unified development workflow

## Requirements

- **Python 3.13+**
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **[Task](https://taskfile.dev/)** - Task runner
- **PostgreSQL** - Database (for full functionality)
- **Docker** (optional) - For containerized deployment

### Core Dependencies

- FastAPI, Strawberry GraphQL, Uvicorn
- SQLModel, SQLAlchemy, Alembic, psycopg
- Pydantic Settings, Typer, Loguru
- Tenacity, Arrow

### Dev Dependencies

- ruff, pytest, pytest-cov, pytest-asyncio, pre-commit

## Quick Start

```bash
# Install prerequisites
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
# Install Task: https://taskfile.dev/installation/

# Setup and run
task setup          # Create virtual environment
task install        # Install dependencies
task run:dev        # Start development server
```

## Build

```bash
task build           # Build Python package (dist/*.whl)
task docker:build    # Build Docker image
task rebuild:all     # Full rebuild: clean, install, test, build, docker
```

## Project Structure

```
src/api_server/
├── api/             # REST endpoints
├── graphql/         # GraphQL schema & resolvers
├── models/          # SQLModel database models
├── services/        # Business logic & DI container
├── events/          # Event types & handlers
├── readiness_pipeline/  # Health check framework
├── event_bus/       # Async event system
├── checks/          # Readiness check implementations
├── app.py           # FastAPI application
├── main.py          # CLI entry point (Typer)
└── settings.py      # Pydantic settings
```

## Development Tasks

```bash
task fct             # Format, check, test
task rebuild:all     # Full rebuild including Docker
task docker:build    # Build Docker image
task db:setup        # Run database migrations
task test            # Run pytest
```

## Configuration

```bash
cp .env.example .env   # Copy and adjust values
```

Environment variables with `API_SERVER_` prefix (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `API_SERVER_PORT` | `8080` | Server port |
| `API_SERVER_DATABASE_URL` | - | PostgreSQL connection string |
| `API_SERVER_LOG_LEVEL` | `INFO` | TRACE/DEBUG/INFO/WARNING/ERROR |
| `API_SERVER_SQL_LOG` | `false` | Enable SQL query logging |
| `API_SERVER_PROFILES` | - | `rest`, `graphql`, or both |

## API Endpoints

- **REST**: http://localhost:8080/docs (Swagger UI)
- **GraphQL**: http://localhost:8080/graphql (GraphiQL)
- **Health**: http://localhost:8080/health-check

## Docker

```bash
task docker:build    # Build image
docker run -e API_SERVER_DATABASE_URL=... -p 8080:8080 api-server
```

## Architecture

- **Readiness Pipeline**: Modular health checks with database, schema, and custom checks
- **Internal Event Bus**: In-process async events with dependency injection
- **Services**: Singleton pattern with dependency injection container
- **Profiles**: Support for `rest` and `graphql` execution profiles

## License

MIT
