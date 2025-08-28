"""Logging configuration for the API server."""

import logging
import os
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages toward loguru."""

    def emit(self, record):
        # Get corresponding loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level=None):
    """Configure loguru logging for the entire application.

    Args:
        log_level: Optional log level to use. If None, will be read from API_SERVER_LOG_LEVEL env var.
    """
    # Get log level from environment if not provided
    if log_level is None:
        log_level = os.getenv("API_SERVER_LOG_LEVEL", "INFO")

    # Ensure log level is uppercase
    log_level = log_level.upper()

    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        #        format=(
        #            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        #            "<level>{level: <8}</level> | "
        #            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        #            "<level>{message}</level>"
        #        ),
        level=log_level,
        colorize=True,
    )

    logger.info(f"Log level set to: {log_level}")

    # Redirect all standard logging to loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Configure all existing loggers to use our handler
    for name in logging.root.manager.loggerDict:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


def setup_sqlalchemy_logging():
    """Configure SQLAlchemy logging to use loguru."""
    # Specifically configure SQLAlchemy loggers
    for logger_name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.base", "sqlalchemy.dialects", "sqlalchemy.pool"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
