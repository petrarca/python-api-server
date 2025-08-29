# Python API server starter project

## Overview

Starter project that demonstrates backend API-server best practices. It exposes functionality as both REST and GraphQL endpoints, uses a clear layered architecture, provides example database models with SQLModel, and shows how to re-use model definitions across API, services, and persistence layers. Comes with uv-based env/deps, Alembic migrations, Ruff, and pytest.

## Current Implementation

- REST endpoints: `/health-check`, `/ping`, `/version` (and a base API router at `/api`)
- GraphQL at `/graphql` with GraphiQL UI
- CLI via `api-server` console command (Typer) and `python -m api_server.main`
- Database layer using SQLModel/SQLAlchemy; migrations via Alembic
- Taskfile-driven workflow (uv venv/install, ruff format/lint, pytest, alembic, run)

## Technology Stack

### Core
- **Language**: Python 3.13+
- **Web Framework**: FastAPI
- **GraphQL**: Strawberry GraphQL (with FastAPI integration)
- **ORM**: SQLModel (SQLAlchemy-based)
- **Database**: PostgreSQL (via psycopg)
- **Migration**: Alembic

### Development Tools
- **Package Manager**: uv (faster alternative to pip)
- **CLI Framework**: Typer
- **Linting & Formatting**: ruff
- **Testing**: pytest
- **Environment**: python-dotenv
- **Logging**: loguru
- **Task Runner**: Taskfile (Go Task)

### Documentation
- **API Docs**: OpenAPI (Swagger UI), ReDoc
- **GraphQL UI**: GraphiQL
- **Templates**: Jinja2

## Project Structure

```
python-api-server/
├── src/
│   └── api_server/                 # Main application package
│       ├── api/                    # REST API endpoints
│       │   ├── api_router.py       # API router configuration
│       │   ├── health_check.py     # /health-check endpoint
│       │   ├── ping.py             # /ping endpoint
│       │   └── version.py          # /version endpoint
│       ├── graphql/                # GraphQL schema and router
│       │   ├── graphql_router.py   # /graphql with GraphiQL
│       │   ├── context.py         # GraphQL context and dependencies
│       │   ├── schema.py          # GraphQL schema definitions (queries, mutations)
│       │   └── types.py           # GraphQL type definitions (Strawberry models)
│       ├── models/                 # Data models (SQLModel)
│       ├── services/               # Business logic and services
│       ├── templates/              # HTML templates (index)
│       ├── app.py                  # FastAPI application setup
│       ├── database.py             # Database connection and utilities
│       ├── logging.py              # Logging configuration
│       └── main.py                 # CLI entry (Typer) and uvicorn runner
├── migrations/                     # Database migrations (Alembic)
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── Taskfile.yml                    # Common development tasks (uv, ruff, pytest, alembic)
├── pyproject.toml                  # Project metadata, deps, tooling
├── setup.py                        # Package setup shim
├── alembic.ini                     # Alembic configuration
├── Dockerfile                      # Containerization
├── docs/                           # Additional docs
└── README.md
```

## Development Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (faster alternative to pip)

### Installation

```bash
# Install dependencies using uv directly
uv pip install -e ".[dev]"

# Or using Task (recommended)
task install
```

### Development Workflow with Task

Backend uses [Task](https://taskfile.dev/) to provide a unified workflow for common development operations. Task is a task runner that allows you to define and run tasks in a simple YAML format.

#### Git Hooks

This project uses pre-commit hooks to ensure code quality before committing. The hooks run the `task fct` command (format, check, test) to ensure that all code is properly formatted, passes linting checks, and tests before being committed.

To install the pre-commit hooks:

```bash
# Install pre-commit hooks
task pre-commit:install
```

This will install hooks that run automatically on `git commit` and `git push` operations. You can also run the hooks manually on all files:

```bash
# Run pre-commit hooks on all files
task pre-commit:run
```

#### Virtual Environment and Package Management

The backend uses [uv](https://github.com/astral-sh/uv) for virtual environment creation and package management. The Taskfile is configured to use uv directly with the Python executable in the virtual environment, avoiding the need to activate the virtual environment manually. This approach ensures compatibility across different shell environments.

#### Available Tasks

This project's Taskfile provides the following commands:

- `task setup` - Create a Python virtual environment using uv
- `task install` - Install the package and development dependencies using uv
- `task clean` - Clean build artifacts
- `task clean:all` - Clean all artifacts including virtual environment
- `task format` - Format code using ruff
- `task lint` - Run ruff linter (auto-fix enabled)
- `task test` - Run tests with pytest
- `task test:cov` - Run tests with coverage report
- `task check` - Run format and lint
- `task build` - Build the package
- `task db:setup` - Setup the database and run all migrations
- `task db:migrate` - Generate a new migration
- `task db:upgrade` - Run all pending migrations
- `task db:downgrade` - Rollback the last migration
- `task db:reset` - Reset the database (WARNING - This will delete all data)
- `task run` - Run the application without auto-reload
- `task run:dev` - Run the application with auto-reload for development
- `task fct` - Format, check, test
- `task pre-commit:install` - Install pre-commit hooks
- `task pre-commit:update` - Update pre-commit hooks
- `task pre-commit:run` - Run pre-commit hooks on all files

Run tasks from the project root, e.g.:

```bash
task run:dev
```

### Development Server

For development with hot reloading (automatically restarts the server when code changes):

```bash
# Start the development server with hot reloading
task run:dev
```

This is the recommended way to run the backend during development as it will automatically reload when you make changes to the code.

### Configuration

The server can be configured using environment variables or command-line arguments. Command-line arguments take precedence over environment variables.

#### Environment Variables

**Required Environment Variables:**

- `API_SERVER_DATABASE_URL`: Database connection string (required) - The application will not start without this variable set. Example: `postgresql+psycopg://username:password@hostname:port/database`

**Optional Environment Variables:**

- `API_SERVER_HOST`: Host to bind the server to (default: "0.0.0.0")
- `API_SERVER_PORT`: Port to bind the server to (default: 8080)
- `API_SERVER_LOG_LEVEL`: Logging level (default: "INFO") - Valid values: TRACE, DEBUG, INFO, WARNING, ERROR
- `API_SERVER_SQL_LOG`: Enable SQL query logging (default: "False") - Valid values: true, 1, yes (case-insensitive)

**Example .env file:**

```
# Server Configuration
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8080

# Logging Configuration
API_SERVER_LOG_LEVEL=INFO
API_SERVER_SQL_LOG=true

# Database Configuration (REQUIRED)
API_SERVER_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres
```

You can set these variables in a `.env` file in the project root directory. An example `.env` file is provided as `.env.example`.

#### Command-line Arguments

- `--host`: Host to bind the server to (overrides API_SERVER_HOST)
- `--port`: Port to bind the server to (overrides API_SERVER_PORT)
- `--log-level`: Logging level (overrides API_SERVER_LOG_LEVEL)
- `--reload`: Enable auto-reload (default: enabled)
- `--no-reload`: Disable auto-reload
- `--sql-log`: Enable SQL query logging (overrides API_SERVER_SQL_LOG)
- `--no-sql-log`: Disable SQL query logging

### Running the Server

```bash
# Run the server with default settings (port 8080)
python -m api_server.main

# Run the server on a specific port
python -m api_server.main --port=8081

# Run the server with custom host
python -m api_server.main --host=127.0.0.1 --port=8080

# Run the server without auto-reload
python -m api_server.main --no-reload

# Using the installed console script (via Typer)
api-server --host=127.0.0.1 --port=8080 --log-level=INFO
```

You can also use the Task runner:

```bash
# Run with default settings
task run

# Run on a specific port
task run -- --port=8080
```

## Database Setup and Migration

The application uses Alembic for database migrations. The following commands are available for database management:

### Setting Up a New Database

```bash
# Configure your database connection in .env file
API_SERVER_DATABASE_URL="postgresql+psycopg://username:password@hostname:port/database"

# Initialize the database with all migrations
task db:setup
```

### Creating a New Migration

After making changes to your database models, create a new migration:

```bash
# Generate a migration with a descriptive message
task db:migrate -- "Add patient addresses table"
```

### Upgrading the Database

To apply all pending migrations:

```bash
task db:upgrade
```

### Downgrading the Database

To roll back the last migration:

```bash
task db:downgrade
```

### Resetting the Database

**Warning**: This will delete all data in the database.

```bash
task db:reset
```

## API Documentation

API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- OpenAPI JSON: http://localhost:8080/openapi.json
- GraphiQL (GraphQL): http://localhost:8080/graphql

## Health Check Endpoint

A simple health check endpoint is available at:
- http://localhost:8080/health-check
- Basic ping: http://localhost:8080/ping
- Version: http://localhost:8080/version

## Deployment

### Docker Deployment

The backend server can be containerized using Docker:

```bash
# Build the Docker image
docker build -t api-server .

# Run the container
docker run -d -p 8080:8080 --name api-server api-server
```

Once running, you can access:
- API: http://localhost:8080
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- Health Check: http://localhost:8080/health-check

The Dockerfile configures the following:
- Exposes port 8080 for the FastAPI application
- Sets environment variables:
  - `API_SERVER_HOST=0.0.0.0`
  - `API_SERVER_LOG_LEVEL=INFO`
- Runs the application with the command: `api-server --host=0.0.0.0 --port=8080 --no-reload`

## Adapting This Template For Your Project

This template is designed to be easily adapted for your own projects. Here's how to customize it for your needs:

### Step-by-Step Guide

Let's say you want to rename the project to `my_server`:

1. **Rename the source directory**:
   ```bash
   # Rename the main package directory
   mv src/api_server src/my_server
   ```

2. **Replace all occurrences of 'api_server' with 'my_server'**:
   - Important: This is case sensitive!
   - Use your IDE's "Replace in Files" feature (in VS Code: Ctrl+Shift+H or Cmd+Shift+H)
   - Search for `api_server` and replace with `my_server` across all files
   - Make sure to update:
     - Python imports
     - Environment variable prefixes
     - Package names in pyproject.toml
     - References in Taskfile.yml
     - Database connection strings
     - Docker configuration

3. **Test if everything is still working**:
   ```bash
   # Run format, check, and tests to verify the project is still functional
   task fct
   
   # Test database migrations
   task db:setup
   ```

4. **Replace example code with your implementations**:
   - Replace the example models in `src/my_server/models/`
   - Update services in `src/my_server/services/`
   - Modify GraphQL schema in `src/my_server/graphql/`
   - Add your API endpoints to `src/my_server/api/`
   - Update database migrations as needed

### Tips for a Smooth Transition

- After renaming, check your `.env` file and update any environment variable prefixes
- Update the console script name in pyproject.toml if you want to change the CLI command
- Remember to regenerate database migrations if you change the models
- Update tests to reflect your new models and business logic

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
