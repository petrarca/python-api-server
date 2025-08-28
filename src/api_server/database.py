"""Database configuration and connection setup."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from sqlmodel import Session, create_engine, text
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Get required database connection info from environment
DATABASE_URL = os.getenv("API_SERVER_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("API_SERVER_DATABASE_URL environment variable is required")

# Enable SQL echo if API_SERVER_SQL_LOG is set
SQL_LOG_STR = os.getenv("API_SERVER_SQL_LOG", "False")
SQL_LOG = SQL_LOG_STR.lower() in ("true", "1", "yes")
logger.info(f"SQL echo is {'enabled' if SQL_LOG else 'disabled'}")

connect_args = {
    "connect_timeout": 10,  # Connection timeout in seconds
}

# Create engine with a small pool size that can be fully closed
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after an hour
    pool_size=5,  # Keep pool small
    max_overflow=10,  # Allow some overflow
    pool_timeout=30,  # Timeout for getting a connection from pool
    echo=SQL_LOG,  # Log SQL
    connect_args=connect_args,
)


def init_db() -> None:
    """Initialize the database, no implicit database table creation."""
    logger.info("Initializing database...")
    # SQLAlchemy logging should already be set up by setup_logging()


def dispose_db() -> None:
    """Dispose of the database engine."""
    logger.info("Closing database connections")
    engine.dispose()


# Implement retry logic for database connections
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, "DEBUG"),
)
@contextmanager
def get_db_session_with_retry() -> Generator[Session, None, None]:
    """
    This function creates a database session with retry logic and yields it to the caller.
    Will attempt to connect to the database with exponential backoff.
    The session is automatically closed when the request is complete,
    thanks to FastAPI's dependency injection system and the context manager.
    """
    try:
        session = Session(engine)
        session_id = id(session)
        try:
            # Test connection
            session.exec(text("SELECT 1"))
            logger.trace(f"Database connection successful for session {session_id}")
            yield session
        except Exception as e:
            logger.error(f"Error during database session {session_id}: {e}")
            raise
        finally:
            session.close()
            logger.trace(f"Database session {session_id} closed and resources released")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        # If we've exhausted retries, reraise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed, please try again later",
        ) from e


def get_db_session() -> Session:
    """Provide a database session for dependency injection."""
    with get_db_session_with_retry() as session:
        yield session


def is_healthy(session: Session) -> dict[str, Any]:
    """Check if the database connection is healthy.

    Args:
        session: The database session to use for the health check.

    Returns:
        A dictionary containing the database health status and connection info.
    """
    try:
        # Execute a simple query to check database connectivity
        result = session.exec(text("SELECT 1"))
        result.one()

        # Get database connection information
        db_info = {
            "status": "healthy",
            "connection": "active",
        }
        return db_info
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection": "failed",
        }
