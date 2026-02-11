# Python API Server Template

A production-ready FastAPI template with REST & GraphQL, readiness pipeline, event bus, admin CLI, and modern tooling.

## Requirements

- **Python 3.14+**
- **[uv](https://github.com/astral-sh/uv)** -- Fast Python package manager
- **[Task](https://taskfile.dev/)** -- Task runner
- **PostgreSQL** -- Database
- **Docker** (optional)

## Quick Start

```bash
task setup          # Create virtual environment
task install        # Install dependencies
cp .env.example .env  # Configure database URL etc.
task db:upgrade     # Run database migrations
task run            # Start server
```

Server starts at http://localhost:8080

## Endpoints

| URL | Description |
|-----|-------------|
| `/docs` | Swagger UI (REST) |
| `/graphql` | GraphiQL (GraphQL) |
| `/health-check` | Health check (GET=cached, POST=fresh) |
| `/ping` | Liveness probe |
| `/version` | Version info |

## CLI

Two entry points provide the same commands:

```bash
# Server (default: starts server without subcommand)
api-server                        # start server
api-server run --reload           # start with auto-reload
api-server check                  # run readiness checks, then exit
api-server cli db check           # validate database status

# Admin CLI (standalone)
api-server-cli db check           # validate database connection + schema
api-server-cli db upgrade         # migrate database (with confirmation)
api-server-cli db upgrade --yes   # migrate without confirmation
```

Via Taskfile:

```bash
task run                          # start server
task run:cli -- db check          # admin CLI
```

## Configuration

Environment variables (`API_SERVER_` prefix), also settable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SERVER_HOST` | `0.0.0.0` | Bind address |
| `API_SERVER_PORT` | `8080` | Port |
| `API_SERVER_DATABASE_URL` | -- | PostgreSQL connection string (required) |
| `API_SERVER_LOG_LEVEL` | `INFO` | TRACE/DEBUG/INFO/WARNING/ERROR |
| `API_SERVER_SQL_LOG` | `false` | SQL query logging |
| `API_SERVER_PROFILES` | -- | `rest`, `graphql`, or both |
| `API_SERVER_RELOAD` | `false` | Auto-reload on code changes |

All settings can be overridden via CLI flags (e.g. `api-server --log-level DEBUG`).

## Development Tasks

```bash
task fct             # Format + lint + test (quick CI)
task test            # Run pytest
task test:cov        # Run with coverage
task format          # Format code (ruff)
task lint            # Lint code (ruff)
task check           # Format + lint (no tests)
task build           # Build Python package
task docker:build    # Build Docker image
task rebuild:all     # Full rebuild: clean, install, test, build, docker
task db:migrate -- "description"   # Generate new migration
task db:upgrade      # Run pending migrations (via alembic directly)
task db:downgrade    # Rollback last migration
```

## Project Structure

```
src/api_server/
├── api/                    # REST endpoints (health, ping, version, patients, addresses)
├── graphql/                # GraphQL schema & resolvers
├── models/                 # Base, DB (SQLModel), and API models
├── services/               # Business logic + DI registry
├── database/               # Connection, alembic utils, advisory locks
├── checks/                 # Readiness check implementations + pipeline builders
├── readiness_pipeline/     # Health check framework (stages, checks, pipeline)
├── event_bus/              # Async event system with DI
├── events/                 # Event types & handlers
├── cli/                    # Admin CLI (db check/upgrade)
│   ├── commands/           # Command groups (db)
│   └── checks/             # CLI-specific pipeline builders + runner
├── utils/                  # Version, model builder/converter, ID generator
├── app.py                  # FastAPI application setup
├── main.py                 # Server entry point (Typer)
├── settings.py             # Pydantic settings
├── constants.py            # Shared constants (profiles, stage names)
├── exceptions.py           # Common exceptions (ResourceNotFound, VersionConflict)
├── exception_handlers.py   # HTTP error mapping (404, 409)
└── logging.py              # Loguru configuration
```

## Docker

```bash
task docker:build
docker run -e API_SERVER_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db \
  -p 8080:8080 api-server
```

## Further Reading

- [Architecture & Design](docs/design/architecture.md)
- [AGENTS.md](AGENTS.md) -- Conventions for AI coding assistants

## License

MIT
