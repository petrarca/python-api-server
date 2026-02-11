"""PostgreSQL advisory lock utilities for coordinating distributed operations.

Provides a context manager pattern for acquiring and releasing PostgreSQL advisory locks,
ensuring only one process can execute a critical section (like migrations or seeding).

Example:
    with advisory_lock(AdvisoryLock.MIGRATION):
        # Only one process enters here
        perform_migration()
"""

from contextlib import contextmanager
from enum import Enum

from loguru import logger
from sqlalchemy import text

from .connection import borrow_db_session


class AdvisoryLock(Enum):
    """Predefined advisory locks for the application.

    Using an enum ensures type safety and ties the lock key to its name.

    Attributes:
        key: PostgreSQL advisory lock integer (must be unique across application)
        name: Descriptive name for logging/debugging

    To add new locks, extend this enum with unique integer keys:
        DATA_SEED = (7239847235, "data_seed")
    """

    MIGRATION = (7239847234, "migration")

    @property
    def key(self) -> int:
        return self.value[0]

    @property
    def lock_name(self) -> str:
        return self.value[1]


@contextmanager
def advisory_lock(lock: AdvisoryLock):
    """Context manager for PostgreSQL advisory locks.

    Ensures only one process can execute a critical section.
    Automatically releases lock on exit (even on exception).

    Args:
        lock: AdvisoryLock enum value (includes both key and name)

    Raises:
        SQLAlchemyError: If lock cannot be acquired or released

    Example:
        with advisory_lock(AdvisoryLock.MIGRATION):
            # Only one process enters here
            perform_migration()
    """
    logger.debug(f"Acquiring advisory lock '{lock.lock_name}' (key={lock.key})...")
    with borrow_db_session() as session:
        try:
            session.exec(text(f"SELECT pg_advisory_lock({lock.key})"))
            logger.debug(f"Advisory lock '{lock.lock_name}' acquired")
            try:
                yield session
            finally:
                logger.debug(f"Releasing advisory lock '{lock.lock_name}'...")
                session.exec(text(f"SELECT pg_advisory_unlock({lock.key})"))
                logger.debug(f"Advisory lock '{lock.lock_name}' released")
        except Exception as e:
            logger.error(f"Error during advisory lock '{lock.lock_name}': {e}")
            raise


@contextmanager
def try_advisory_lock(lock: AdvisoryLock):
    """Context manager for non-blocking PostgreSQL advisory lock attempt.

    Tries to acquire a lock using pg_try_advisory_lock(). If lock is not available,
    the context manager yields None, allowing callers to skip or retry.

    Args:
        lock: AdvisoryLock enum value

    Yields:
        Session if lock acquired, None if lock not available

    Example:
        with try_advisory_lock(AdvisoryLock.MIGRATION) as session:
            if session is not None:
                # We have the lock, do work
                perform_migration()
            else:
                # Another process has the lock, skip
                logger.info("Skipping, another process holds the lock")
    """
    logger.debug(f"Trying advisory lock '{lock.lock_name}' (key={lock.key})...")
    with borrow_db_session() as session:
        result = session.exec(text(f"SELECT pg_try_advisory_lock({lock.key})"))
        lock_acquired = result.scalar()
        if lock_acquired:
            logger.debug(f"Advisory lock '{lock.lock_name}' acquired")
            try:
                yield session
            finally:
                logger.debug(f"Releasing advisory lock '{lock.lock_name}'...")
                session.exec(text(f"SELECT pg_advisory_unlock({lock.key})"))
                logger.debug(f"Advisory lock '{lock.lock_name}' released")
        else:
            logger.debug(f"Advisory lock '{lock.lock_name}' not available (another process holds it)")
            yield None
