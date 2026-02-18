"""Main FastAPI application module."""

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
        logger.error("Server state: {}", health_result.server_state)
        raise SystemExit(1)
    elif health_result.server_state == ServerState.DEGRADED:
        logger.warning("Server starting in degraded state - some non-critical features unavailable")
        logger.info("Server state: {}", health_result.server_state)
    else:  # OPERATIONAL
        logger.info("All startup readiness checks passed successfully")
        logger.info("Server state: {}", health_result.server_state)


def _log_server_endpoints_summary(settings: Settings, active_profiles: set[str]) -> None:
    """Log a comprehensive summary of server URL and available endpoints.

    Args:
        settings: Application settings containing host and port
        active_profiles: Set of active profile names
    """
    server_url = f"http://{settings.host}:{settings.port}"
    logger.info("Server running at: {}", server_url)

    endpoints = [
        ("Home", "/"),
        ("Health Check", "/health-check"),
        ("Ping", "/ping"),
        ("Version", "/version"),
        ("OpenAPI Schema", "/openapi.json"),
        ("API Docs", "/docs"),
        ("ReDoc", "/redoc"),
    ]

    if PROFILE_REST in active_profiles:
        endpoints.append(("REST API", "/api"))

    if PROFILE_GRAPHQL in active_profiles:
        endpoints.append(("GraphQL", "/graphql"))
        endpoints.append(("GraphQL Playground", "/graphql/playground"))

    logger.info("Available endpoints:")
    for name, path in endpoints:
        logger.info("   {}: {}", name, f"{server_url}{path}")

    logger.info("Active profiles: {}", ", ".join(sorted(active_profiles)))


async def perform_startup_checks(app_settings: Settings) -> None:
    """Perform startup readiness checks without starting the server.

    This function contains the same logic that runs during server startup,
    but can be called independently for check-only mode.

    Args:
        app_settings: Application settings

    Raises:
        SystemExit: If readiness checks fail
    """
    active_profile = parse_profile(app_settings.profiles)
    set_active_profiles(active_profile)

    setup_logging(log_level=app_settings.log_level)
    setup_sqlalchemy_logging()

    logger.info("Registering services in the service registry")
    registry = get_service_registry()
    register_all_services(registry)

    logger.info("API server performing startup checks")
    health_result = get_health_check_service().perform_health_check()
    _log_startup_check_results(health_result)


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """Handle startup and shutdown events for the main application."""
    settings = get_settings()
    _app.state.settings = settings  # type: ignore[attr-defined]

    from api_server.events import register_event_handlers

    registry = get_service_registry()
    register_all_services(registry)
    register_event_handlers()

    await perform_startup_checks(settings)

    active_profiles = parse_profile(settings.profiles)
    _app.state.active_profiles = active_profiles  # type: ignore[attr-defined]

    # Mount profile-dependent routers now that settings are fully resolved
    if PROFILE_REST in active_profiles:
        _app.include_router(api_router, prefix="/api")

    if PROFILE_GRAPHQL in active_profiles:
        from api_server.graphql.graphql_router import create_graphql_router

        _app.include_router(create_graphql_router(), prefix="/graphql")

    # Initialise templates and store on app state for use by route handlers
    import os

    template_dir = os.path.join(os.path.dirname(__file__), "home")
    _app.state.templates = Jinja2Templates(directory=template_dir)  # type: ignore[attr-defined]

    _log_server_endpoints_summary(settings, active_profiles)

    yield

    logger.info("API server shutting down")
    get_event_bus().shutdown()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# System endpoints — always enabled, profile-independent
app.include_router(health_router, prefix="")
app.include_router(ping_router, prefix="")
app.include_router(version_router, prefix="/version")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the index template at root."""
    health_service = get_health_check_service()
    server_state = health_service.get_server_state().value

    version_info = get_version()
    active_profile = get_active_profiles()

    context = {
        "request": request,
        "version": version_info.version,
        "full_version": version_info.full_version,
        "server_state": server_state,
        "build_timestamp": version_info.build_timestamp,
        "profile": active_profile,
        "profile_display": ", ".join(sorted(active_profile)),
    }
    return request.app.state.templates.TemplateResponse(request, "index.html", context)


def get_app_settings() -> Settings:
    """FastAPI dependency helper returning current app Settings."""
    return get_settings()
