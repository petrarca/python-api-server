"""CLI entry point.

Usage:
    python -m api_server.cli db check
    python -m api_server.cli db upgrade
    api-server-cli db check
    api-server-cli db upgrade
"""

import sys

from loguru import logger

import api_server
from api_server.cli.app import app


def _configure_cli_logging() -> None:
    """Configure loguru for CLI (compact format: level + message, no timestamps)."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    # Enable logging for the server package
    logger.enable(api_server.__name__)


def main() -> None:
    """CLI entry point with logging configuration."""
    _configure_cli_logging()
    app()


if __name__ == "__main__":
    main()
