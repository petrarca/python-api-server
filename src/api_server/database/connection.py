"""Database configuration and connection setup.

Refactored to lazily create the SQLModel engine after application settings
have been loaded / possibly overridden by CLI flags. This prevents premature
failure on import when `API_SERVER_DATABASE_URL` is not yet set or will be
provided via command line.
"""

from collections.abc import Generator
from contextlib import contextmanager

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
    logger.info("SQL echo is {}", "enabled" if settings.sql_log else "disabled")
    return engine_local


def get_engine():  # type: ignore[return-value]
    """Return a singleton engine instance, creating it lazily.

    If the engine exists but connections fail, it will be disposed and recreated.
    This handles cases where the database wasn't ready when the engine was first created.
    """
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def is_initialized() -> bool:
    """Check if database already initialized"""
    global _engine
    return _engine is not None


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


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, "DEBUG"),
)
def _create_session() -> Session:
    """Create a database session with retry logic.

    This function handles connection failures by disposing and recreating
    the engine on each retry attempt. It is separate from the context
    manager to allow proper retry behavior.

    Returns:
        Session: A new database session

    Raises:
        Exception: If all retry attempts fail
    """
    global _engine
    try:
        session = Session(get_engine())
        # Test the connection immediately
        session.execute(text("SELECT 1"))
        return session
    except Exception as e:
        # Connection failed - dispose engine so it can be recreated on retry
        if _engine is not None:
            logger.warning("Database connection failed, disposing engine for retry...")
            _engine.dispose()
            _engine = None
        logger.error("Failed to create database session: {}", e)
        raise


@contextmanager
def borrow_db_session() -> Generator[Session]:
    """Public context manager for ad-hoc database usage.

    Creates a database session with retry logic and yields it to the caller.
    Will attempt to connect to the database with exponential backoff.
    If the database is not ready, it will retry up to 5 times.

    Use this function for health checks, utility scripts, or any
    non-FastAPI context. For FastAPI route handlers, use get_db_session()
    as a dependency instead.

    Example:
        from . import borrow_db_session
        with borrow_db_session() as session:
            session.exec(text("SELECT 1"))
    """
    # Use the retry-wrapped session creation
    session = _create_session()
    session_id = id(session)

    try:
        yield session
    except Exception as e:  # noqa: BLE001
        logger.error("Error during database session {}: {}", session_id, e)
        raise
    finally:
        session.close()
        logger.trace("Database session {} closed and resources released", session_id)


def get_db_session() -> Session:
    """FastAPI dependency yielding a database session.

    Usage in route:
        def endpoint(session: Session = Depends(get_db_session)): ...
    """
    with borrow_db_session() as session:
        yield session
