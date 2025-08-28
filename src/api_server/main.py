"""Main entry point for the API server."""

import os
from enum import Enum

import typer
import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()


def get_env_var(name: str, default: str) -> str:
    """Get environment variable or return default value."""
    return os.environ.get(name, default)


class LogLevel(str, Enum):
    """Log level enum for typer."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


app = typer.Typer()


# Define default option values
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SQL_LOG = False

# Define Typer options
HOST_OPTION = typer.Option(None, help="Host to bind the server to (env: API_SERVER_HOST)", metavar="<server>")
PORT_OPTION = typer.Option(None, help="Port to bind the server to (env: API_SERVER_PORT)", metavar="<port>")
RELOAD_OPTION = typer.Option(True, help="Enable/disable auto-reload")
LOG_LEVEL_OPTION = typer.Option(None, help="Log level (env: API_SERVER_LOG_LEVEL)", metavar="<level>", case_sensitive=False)
SQL_LOG_OPTION = typer.Option(None, help="Enable/disable SQL query logging (env: API_SERVER_SQL_LOG)")


@app.command()
def run(
    host: str = HOST_OPTION,
    port: int = PORT_OPTION,
    reload: bool = RELOAD_OPTION,
    log_level: LogLevel = LOG_LEVEL_OPTION,
    sql_log: bool = SQL_LOG_OPTION,
) -> None:
    """Run the application using uvicorn server."""
    # Get values from environment variables if not provided via CLI
    actual_host = host or get_env_var("API_SERVER_HOST", DEFAULT_HOST)
    actual_port = port or int(get_env_var("API_SERVER_PORT", str(DEFAULT_PORT)))
    actual_log_level = log_level or get_env_var("API_SERVER_LOG_LEVEL", DEFAULT_LOG_LEVEL)

    # For boolean flags, we need to check if it's None (not provided via CLI)
    actual_sql_log = get_env_var("API_SERVER_SQL_LOG", str(DEFAULT_SQL_LOG)).lower() in ("true", "1", "yes") if sql_log is None else sql_log

    # Set log level and SQL log from command line
    os.environ["API_SERVER_LOG_LEVEL"] = actual_log_level.upper()
    os.environ["API_SERVER_SQL_LOG"] = str(actual_sql_log)

    logger.info(f"Starting API server at http://{actual_host}:{actual_port}")
    logger.info(f"Log level: {actual_log_level.upper()}")
    logger.info(f"SQL logging: {'enabled' if actual_sql_log else 'disabled'}")

    # Configure uvicorn logging to use loguru
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(levelprefix)s %(message)s"

    uvicorn.run(
        "api_server.app:app",
        host=actual_host,
        port=actual_port,
        reload=reload,
        log_level=actual_log_level.lower(),
        log_config=log_config,
    )


if __name__ == "__main__":
    app()
