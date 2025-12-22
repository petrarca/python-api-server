"""Main entry point for the API server using Typer and Pydantic Settings."""

import typer
import uvicorn
from loguru import logger

from api_server.logging import setup_logging
from api_server.settings import get_settings

app = typer.Typer()


HOST_OPTION = typer.Option(
    None,
    help="Host to bind the server to (overrides API_SERVER_HOST)",
    metavar="<server>",
)  # fmt: skip
PORT_OPTION = typer.Option(
    None,
    help="Port to bind the server to (overrides API_SERVER_PORT)",
    metavar="<port>",
)  # fmt: skip
RELOAD_OPTION = typer.Option(
    None,
    help="Enable/disable auto-reload (overrides API_SERVER_RELOAD)",
)  # fmt: skip
LOG_LEVEL_OPTION = typer.Option(
    None,
    help="Log level (overrides API_SERVER_LOG_LEVEL)",
    metavar="<level>",
    case_sensitive=False,
)  # fmt: skip
SQL_LOG_OPTION = typer.Option(
    None,
    help="Enable/disable SQL query logging (overrides API_SERVER_SQL_LOG)",
)  # fmt: skip
DATABASE_URL_OPTION = typer.Option(
    None,
    help="Database URL (overrides API_SERVER_DATABASE_URL)",
    metavar="<dsn>",
)  # fmt: skip
PROFILE_OPTION = typer.Option(
    None,
    "-p",
    "--profile",
    help="Server profile: rest, graphql, or combination (e.g., 'rest,graphql'). Omit for all.",
    metavar="<profile>",
)  # fmt: skip
CHECK_ONLY_OPTION = typer.Option(
    None,
    "--check-only",
    help="Run readiness checks only, then exit (without starting server)",
    flag_value=True,
)  # fmt: skip


def _update_settings(
    host: str | None,
    port: int | None,
    log_level: str | None,
    reload: bool | None,
    sql_log: bool | None,
    database_url: str | None,
    profiles: str | None,
) -> None:
    """Update settings with CLI overrides.

    Args:
        host: Host override
        port: Port override
        log_level: Log level override
        reload: Reload override
        sql_log: SQL logging override
        database_url: Database URL override
        profiles: Profile configuration override
    """
    settings = get_settings()

    # Apply overrides
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port
    if log_level is not None:
        settings.log_level = log_level
    if reload is not None:
        settings.reload = reload
    if sql_log is not None:
        settings.sql_log = sql_log
    if database_url is not None:
        settings.database_url = database_url
    if profiles is not None:
        settings.profiles = profiles


@app.command()
def run(
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    reload: bool = RELOAD_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
    database_url: str = DATABASE_URL_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Run the API server."""
    # Update settings with CLI overrides
    _update_settings(host, port, log_level, reload, sql_log, database_url, profile)

    # Get final settings
    settings = get_settings()

    # Setup logging
    setup_logging(settings.log_level)

    logger.info(f"Starting API server on {settings.host}:{settings.port}")
    logger.info(f"Profile: {settings.profiles or 'all'}")
    logger.info(f"Reload: {settings.reload}")

    # Run the app - use import string for reload mode
    if settings.reload:
        uvicorn.run(
            "api_server.app:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            log_level=settings.log_level.lower(),
        )
    else:
        from api_server.app import app as fastapi_app

        uvicorn.run(
            fastapi_app,
            host=settings.host,
            port=settings.port,
            reload=False,
            log_level=settings.log_level.lower(),
        )


@app.command()
def check(
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
    database_url: str = DATABASE_URL_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Run readiness checks only."""
    # Update settings with CLI overrides
    _update_settings(host, port, log_level, False, sql_log, database_url, profile)

    # Get final settings
    settings = get_settings()

    # Setup logging
    setup_logging(settings.log_level)

    logger.info("Running readiness checks only")

    # Import and run checks
    import asyncio

    from api_server.app import perform_startup_checks

    try:
        asyncio.run(perform_startup_checks(settings))
        logger.info("Readiness checks completed successfully")
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Readiness checks failed: {e}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    app()
