"""Main entry point for the API server using Typer and Pydantic Settings."""

import typer
import uvicorn
from loguru import logger

from api_server.settings import Settings, get_settings

app = typer.Typer()


HOST_OPTION = typer.Option(None, help="Host to bind the server to (overrides API_SERVER_HOST)", metavar="<server>")
PORT_OPTION = typer.Option(None, help="Port to bind the server to (overrides API_SERVER_PORT)", metavar="<port>")
RELOAD_OPTION = typer.Option(None, help="Enable/disable auto-reload (overrides API_SERVER_RELOAD)")
LOG_LEVEL_OPTION = typer.Option(None, help="Log level (overrides API_SERVER_LOG_LEVEL)", metavar="<level>", case_sensitive=False)
SQL_LOG_OPTION = typer.Option(None, help="Enable/disable SQL query logging (overrides API_SERVER_SQL_LOG)")


def _override_settings(
    base: Settings,
    host: str | None,
    port: int | None,
    reload: bool | None,
    log_level: str | None,
    sql_log: bool | None,
) -> Settings:
    """Return a new Settings object with CLI overrides applied."""
    data = base.model_dump()
    if host is not None:
        data["host"] = host
    if port is not None:
        data["port"] = port
    if reload is not None:
        data["reload"] = reload
    if log_level is not None:
        data["log_level"] = log_level.upper()
    if sql_log is not None:
        data["sql_log"] = sql_log
    return Settings(**data)


@app.command()
def run(
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    reload: bool = RELOAD_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
) -> None:
    """Run the application using uvicorn server with centralized settings."""
    base_settings = get_settings()
    settings = _override_settings(base_settings, host, port, reload, log_level, sql_log)

    logger.info(f"Starting API server at http://{settings.host}:{settings.port}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"SQL logging: {'enabled' if settings.sql_log else 'disabled'}")

    if settings.log_level in {"DEBUG", "TRACE"}:
        # Safe dump (no secrets yet). If secrets added later, exclude them.
        logger.debug(f"Effective settings: {settings.model_dump()}")

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(levelprefix)s %(message)s"

    # Pass settings through uvicorn.run; service layer can access via dependency (app.state later)
    uvicorn.run(
        "api_server.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        log_config=log_config,
    )


if __name__ == "__main__":  # pragma: no cover
    app()
