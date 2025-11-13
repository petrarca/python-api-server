"""Main FastAPI application module."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from api_server.api import api_router
from api_server.api.health_check import router as health_router
from api_server.api.ping import router as ping_router
from api_server.api.version import router as version_router
from api_server.database import dispose_db, init_db
from api_server.graphql.graphql_router import create_graphql_router
from api_server.logging import setup_logging, setup_sqlalchemy_logging
from api_server.services.address_service import AddressService, get_address_service
from api_server.services.health_check_service import HealthCheckService, get_health_check_service
from api_server.services.patient_service import PatientService, get_patient_service
from api_server.services.registry import get_service_registry
from api_server.settings import Settings, get_settings
from api_server.utils.version import get_version


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Handle startup and shutdown events for the FastAPI application."""
    # Load settings and attach to app state (so dependencies can access)
    settings = get_settings()
    _app.state.settings = settings  # type: ignore[attr-defined]

    # Configure logging on startup
    setup_logging(log_level=settings.log_level)
    setup_sqlalchemy_logging()

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {str(e)}")
        logger.warning("Application will continue to start, but database-dependent features may not work")

    # Register services in the service registry
    logger.info("Registering services in the service registry")
    registry = get_service_registry()
    # Register factory methods:
    registry.register_factory(HealthCheckService, get_health_check_service)
    registry.register_factory(PatientService, get_patient_service)
    registry.register_factory(AddressService, get_address_service)

    # Log startup message
    logger.info("API server starting up")

    # Run server readiness checks, including initializing database
    get_health_check_service().perform_health_check()

    yield

    # Log shutdown message
    logger.info("API server shutting down")

    # Dispose database connection(s) and engine
    dispose_db()


app = FastAPI(
    lifespan=lifespan,
    title="API server starter project",
    description="Backend starter project with GraphQL, REST endpoints and access to PostgreSQL database",
    version=get_version().version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Initialize templates
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health router
app.include_router(health_router, prefix="")

# Include ping router
app.include_router(ping_router, prefix="")

# Include main API router
app.include_router(api_router, prefix="/api")

# Include version router
app.include_router(version_router, prefix="/version")

# Initialize GraphQL router with the schema
graphql_router = create_graphql_router()

# Include the GraphQL router
app.include_router(graphql_router, prefix="/graphql")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the index template at root."""
    # Get the current server state
    health_service = get_health_check_service()
    server_state = health_service.get_server_state().value

    # Extract build timestamp from version if available
    version_info = get_version()
    build_timestamp = version_info.build_timestamp

    context = {
        "request": request,
        "version": version_info.version,
        "full_version": version_info.full_version,
        "server_state": server_state,
        "build_timestamp": build_timestamp,
    }
    return templates.TemplateResponse("index.html", context)


def get_app_settings() -> Settings:
    """FastAPI dependency helper returning current app Settings."""
    return get_settings()
