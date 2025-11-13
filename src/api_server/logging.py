"""Logging configuration for the API server."""

import logging
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


def setup_logging(log_level: str):
    """Configure loguru logging for the entire application.

    Args:
        log_level: Log level to use (from settings, which handles env vars and CLI args).
    """
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
    for name in logging.Logger.manager.loggerDict:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # Set third-party library loggers to the same level as the application
    # This gives consistent behavior - user controls all logging with one setting
    for noisy_logger in ("httpcore", "httpx", "openai", "urllib3", "asyncio", "api_server"):
        logging.getLogger(noisy_logger).setLevel(log_level)


def setup_sqlalchemy_logging():
    """Configure SQLAlchemy logging to use loguru."""
    # Specifically configure SQLAlchemy loggers
    for logger_name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.base", "sqlalchemy.dialects", "sqlalchemy.pool"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
