"""Main entry point for the API server using Typer and Pydantic Settings."""

import typer
import uvicorn
from loguru import logger

from api_server.cli import app as cli_app
from api_server.logging import setup_logging
from api_server.settings import get_settings

app = typer.Typer(invoke_without_command=True)


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

    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port
    if log_level is not None:
        # Validate log level
        log_level_upper = log_level.upper()
        allowed = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR"}
        if log_level_upper not in allowed:
            raise ValueError(f"Invalid log level: {log_level}. Must be one of: {', '.join(sorted(allowed))}")
        settings.log_level = log_level_upper  # type: ignore[assignment]
    if reload is not None:
        settings.reload = reload
    if sql_log is not None:
        settings.sql_log = sql_log
    if database_url is not None:
        settings.database_url = database_url
    if profiles is not None:
        settings.profiles = profiles


def _prepare_and_log_settings(
    host: str | None,
    port: int | None,
    log_level: str | None,
    reload: bool | None,
    sql_log: bool | None,
    database_url: str | None,
    profile: str | None,
) -> None:
    """Prepare settings and log startup information."""
    _update_settings(host, port, log_level, reload, sql_log, database_url, profile)

    # Set up logging immediately after settings are updated
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(f"Log level: {settings.log_level}")

    if settings.log_level in {"DEBUG", "TRACE"}:
        logger.debug(f"Effective settings: {settings.model_dump()}")


def _run_server(
    host: str | None,
    port: int | None,
    log_level: str | None,
    reload: bool | None,
    sql_log: bool | None,
    database_url: str | None,
    profile: str | None,
) -> None:
    """Start the uvicorn server."""
    _prepare_and_log_settings(host, port, log_level, reload, sql_log, database_url, profile)

    settings = get_settings()
    logger.info(f"Starting API server at http://{settings.host}:{settings.port}")

    uvicorn.run(
        "api_server.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=str(settings.log_level).lower(),
    )


def _run_checks(
    host: str | None,
    port: int | None,
    log_level: str | None,
    sql_log: bool | None,
    database_url: str | None,
    profile: str | None,
) -> None:
    """Run readiness checks only."""
    _prepare_and_log_settings(host, port, log_level, False, sql_log, database_url, profile)

    settings = get_settings()
    logger.info("Running readiness checks only - server will not start")

    import asyncio

    from api_server.app import perform_startup_checks

    asyncio.run(perform_startup_checks(settings))
    logger.info("Readiness checks completed successfully - exiting")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    reload: bool = RELOAD_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
    database_url: str = DATABASE_URL_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """API Server - Default: run the server."""
    if ctx.invoked_subcommand is None:
        # No subcommand specified, run the server (default behavior)
        _run_server(host, port, log_level, reload, sql_log, database_url, profile)


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
    """Run the server."""
    _run_server(host, port, log_level, reload, sql_log, database_url, profile)


@app.command()
def check(
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
    database_url: str = DATABASE_URL_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Run readiness checks only, then exit (without starting server)."""
    _run_checks(host, port, log_level, sql_log, database_url, profile)


app.add_typer(cli_app, name="cli", invoke_without_command=True)


if __name__ == "__main__":  # pragma: no cover
    app()
