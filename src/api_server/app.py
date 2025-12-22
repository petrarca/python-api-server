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
from api_server.constants import PROFILE_GRAPHQL, PROFILE_REST
from api_server.database import dispose_db
from api_server.event_bus import get_event_bus
from api_server.exception_handlers import register_exception_handlers
from api_server.logging import setup_logging, setup_sqlalchemy_logging
from api_server.profile import get_active_profiles, parse_profile, set_active_profiles
from api_server.services.di import register_all_services
from api_server.services.health_check_service import get_health_check_service
from api_server.services.registry import get_service_registry
from api_server.settings import Settings, get_settings
from api_server.utils.version import get_version


def _log_startup_check_results(health_result) -> None:
    """Log a concise summary of startup check results.

    Args:
        health_result: HealthCheckResult from pipeline execution
    """
    from api_server.readiness_pipeline.enums import ServerState

    if health_result.server_state == ServerState.ERROR:
        logger.error("Startup readiness checks failed - critical infrastructure issues")
        logger.error(f"Server state: {health_result.server_state}")
        raise SystemExit(1)
    elif health_result.server_state == ServerState.DEGRADED:
        logger.warning("Server starting in degraded state - some non-critical features unavailable")
        logger.info(f"Server state: {health_result.server_state}")
    else:  # OPERATIONAL
        logger.info("All startup readiness checks passed successfully")
        logger.info(f"Server state: {health_result.server_state}")


def _log_server_endpoints_summary(settings: Settings, active_profiles: set[str]) -> None:
    """Log a comprehensive summary of server URL and available endpoints.

    Args:
        settings: Application settings containing host and port
        active_profiles: Set of active profile names
    """
    # Log the main server URL
    server_url = f"http://{settings.host}:{settings.port}"
    logger.info(f"Server running at: {server_url}")

    # Collect all available endpoints
    endpoints = []

    # System endpoints - always available
    endpoints.extend(
        [
            ("Home", "/"),
            ("Health Check", "/health-check"),
            ("Ping", "/ping"),
            ("Version", "/version"),
            ("OpenAPI Schema", "/openapi.json"),
            ("API Docs", "/docs"),
            ("ReDoc", "/redoc"),
        ]
    )

    # Profile-based endpoints
    if PROFILE_REST in active_profiles:
        endpoints.append(("REST API", "/api"))

    if PROFILE_GRAPHQL in active_profiles:
        endpoints.append(("GraphQL", "/graphql"))
        endpoints.append(("GraphQL Playground", "/graphql/playground"))

    # Log endpoints summary
    logger.info("Available endpoints:")
    for name, path in endpoints:
        full_url = f"{server_url}{path}"
        logger.info(f"   {name}: {full_url}")

    # Log active profiles
    profile_display = ", ".join(sorted(active_profiles))
    logger.info(f"Active profiles: {profile_display}")


async def perform_startup_checks(app_settings: Settings) -> None:
    """Perform startup readiness checks without starting the server.

    This function contains the same logic that runs during server startup,
    but can be called independently for check-only mode.

    Args:
        app_settings: Application settings

    Raises:
        SystemExit: If readiness checks fail
    """
    # Parse and store active profile in app state (parse once, reuse throughout)
    active_profile = parse_profile(app_settings.profiles)

    # Set active profiles globally for access throughout the app
    set_active_profiles(active_profile)

    # Configure logging on startup with log level from settings
    setup_logging(log_level=app_settings.log_level)
    setup_sqlalchemy_logging()

    # Register services in the service registry
    logger.info("Registering services in the service registry")
    registry = get_service_registry()
    # Register all services using shared DI module
    register_all_services(registry)

    # Log startup message
    logger.info("API server performing startup checks")

    # Run server readiness checks
    health_result = get_health_check_service().perform_health_check()

    # Use pipeline's server state determination - only exit on critical failures
    _log_startup_check_results(health_result)


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """Handle startup and shutdown events for the main application."""
    # Load settings and attach to app state (so dependencies can access)
    settings = get_settings()
    _app.state.settings = settings  # type: ignore[attr-defined]

    # Initialize ServiceRegistry and register event handlers
    from api_server.events import register_event_handlers
    from api_server.services.di import register_all_services
    from api_server.services.registry import get_service_registry

    registry = get_service_registry()
    register_all_services(registry)
    register_event_handlers()

    # Perform startup checks (same logic as check-only mode)
    await perform_startup_checks(settings)

    # Log comprehensive server URL and endpoints summary
    _log_server_endpoints_summary(settings, parse_profile(settings.profiles))

    # Store active profile in app state for runtime access
    _app.state.active_profile = parse_profile(settings.profiles)  # type: ignore[attr-defined]

    yield

    # Log shutdown message
    logger.info("API server shutting down")

    # Shutdown event bus
    get_event_bus().shutdown()

    # Dispose database connections
    dispose_db()


@asynccontextmanager
async def combined_lifespan(_app: FastAPI):
    """FastAPI lifespan for the API server."""
    async with app_lifespan(_app):
        yield


app = FastAPI(
    lifespan=combined_lifespan,
    title="API server starter project",
    description="Backend starter project with GraphQL, REST endpoints and access to PostgreSQL database",
    version=get_version().version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Get settings and parse profile configuration once (parse once, reuse throughout)
global_settings = get_settings()
profile = parse_profile(global_settings.profiles)

# Initialize home page templates
template_dir = os.path.join(os.path.dirname(__file__), "home")
templates = Jinja2Templates(directory=template_dir)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# System endpoints - always enabled
app.include_router(health_router, prefix="")
app.include_router(ping_router, prefix="")
app.include_router(version_router, prefix="/version")


# Profile-based endpoints
if PROFILE_REST in profile:
    app.include_router(api_router, prefix="/api")

if PROFILE_GRAPHQL in profile:
    from api_server.graphql.graphql_router import create_graphql_router

    graphql_router = create_graphql_router()
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

    # Get active profiles from app state
    active_profile = get_active_profiles()

    # Display profile: show the active profiles as comma-separated list
    active_profile_display = ", ".join(sorted(active_profile))

    context = {
        "request": request,
        "version": version_info.version,
        "full_version": version_info.full_version,
        "server_state": server_state,
        "build_timestamp": build_timestamp,
        "profile": active_profile,
        "profile_display": active_profile_display,
    }
    return templates.TemplateResponse(request, "index.html", context)


def get_app_settings() -> Settings:
    """FastAPI dependency helper returning current app Settings."""
    return get_settings()
