"""Common utilities for metadata loaders.

Provides shared functionality for loading metadata from filesystem into database,
including transaction handling and mtime-based synchronization.
"""

from collections.abc import Callable
from contextlib import contextmanager

import arrow
from loguru import logger
from sqlmodel import Session

from api_server.models.metadata_model import LoadResult


@contextmanager
def handle_transaction(session: Session, result: LoadResult, operation_name: str = "Load"):
    """Context manager for handling database transactions with LoadResult.

    Automatically commits on success or rolls back on errors.
    Logs appropriate messages based on the result.

    Args:
        session: Database session
        result: LoadResult to track success/failure
        operation_name: Name of operation for logging (e.g., "Load", "Sync")

    Example:
        result = LoadResult()
        with handle_transaction(session, result, "Load"):
            # Perform operations that modify result
            result.created += 1
            session.add(item)
    """
    try:
        yield
    except Exception as e:
        session.rollback()
        logger.error("{} failed with exception: {}", operation_name, e)
        result.failed += 1
        result.errors.append(f"Transaction error: {str(e)}")
        raise
    else:
        # Commit or rollback based on result state
        if result.failed == 0:
            session.commit()
            logger.info(
                "{} complete: {} created, {} updated, {} skipped",
                operation_name,
                result.created,
                result.updated,
                result.skipped,
            )
        else:
            session.rollback()
            logger.error(
                "{} failed: {} errors, transaction rolled back. Successful operations: {} created, {} updated, {} skipped",
                operation_name,
                result.failed,
                result.created,
                result.updated,
                result.skipped,
            )
            if result.errors:
                logger.error("{} errors:\n{}", operation_name, "\n".join(f"  - {err}" for err in result.errors))


def should_update_from_mtime(file_mtime_timestamp: float, db_updated_at) -> bool:
    """Determine if file should update database based on modification times.

    Args:
        file_mtime_timestamp: File modification time (Unix timestamp)
        db_updated_at: Database record's updated_at timestamp (datetime or None)

    Returns:
        True if file is newer and should update DB, False otherwise
    """
    file_mtime = arrow.get(file_mtime_timestamp)

    if db_updated_at is None:
        # No DB record - should create
        return True

    db_updated = arrow.get(db_updated_at)
    return file_mtime > db_updated


def process_items_with_transaction(
    session: Session,
    items: list[str],
    processor: Callable[[str, LoadResult], None],
    operation_name: str = "Load",
) -> LoadResult:
    """Process a list of items in a single transaction.

    Generic helper that processes items and handles transaction management.

    Args:
        session: Database session
        items: List of item identifiers to process
        processor: Function that processes one item and updates result
                  Signature: (item_key: str, result: LoadResult) -> None
        operation_name: Name of operation for logging

    Returns:
        LoadResult with counts and errors

    Example:
        def process_template(key: str, result: LoadResult):
            # Load and sync template
            result.created += 1

        result = process_items_with_transaction(
            session, template_keys, process_template, "Template Load"
        )
    """
    result = LoadResult()

    if not items:
        logger.info("No items found for {}", operation_name.lower())
        return result

    logger.info("{}: processing {} items", operation_name, len(items))

    with handle_transaction(session, result, operation_name):
        for item in items:
            processor(item, result)

    return result
