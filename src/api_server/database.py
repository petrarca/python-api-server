"""Database configuration and connection setup.

Refactored to lazily create the SQLModel engine after application settings
have been loaded / possibly overridden by CLI flags. This prevents premature
failure on import when `API_SERVER_DATABASE_URL` is not yet set or will be
provided via command line.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from sqlmodel import Session, create_engine, text
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from api_server.settings import get_settings

_engine = None  # type: ignore[var-annotated]


def _build_engine():  # type: ignore[return-value]
    """Create and return a new engine from current settings.

    Raises:
        ValueError: if database URL not configured.
    """
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        raise ValueError("Database URL missing: provide API_SERVER_DATABASE_URL env or --database-url CLI argument")
    connect_args = {"connect_timeout": 10}
    engine_local = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=settings.sql_log,
        connect_args=connect_args,
    )
    logger.info(f"SQL echo is {'enabled' if settings.sql_log else 'disabled'}")
    return engine_local


def get_engine():  # type: ignore[return-value]
    """Return a singleton engine instance, creating it lazily."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def init_db() -> None:
    """Initialize the database, no implicit database table creation."""
    logger.info("Initializing database...")
    # SQLAlchemy logging should already be set up by setup_logging()


def dispose_db() -> None:
    """Dispose of the database engine if it was created."""
    global _engine
    if _engine is not None:
        logger.info("Closing database connections")
        _engine.dispose()
        _engine = None


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
        session = Session(get_engine())
        session_id = id(session)
        try:
            # Test connection
            session.exec(text("SELECT 1"))
            logger.trace(f"Database connection successful for session {session_id}")
            yield session
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error during database session {session_id}: {e}")
            raise
        finally:
            session.close()
            logger.trace(f"Database session {session_id} closed and resources released")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to connect to database: {e}")
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
