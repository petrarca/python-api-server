"""Database package for API server.

This package provides database connection utilities and alembic management tools.
All functions from connection.py are re-exported for backward compatibility.
"""

# Re-export connection functions for backward compatibility
# Export alembic utilities
from .alembic_utils import AlembicManager
from .connection import borrow_db_session, dispose_db, get_db_session, get_engine, init_db, is_initialized

__all__ = [
    # Connection functions (re-exported from connection.py)
    "borrow_db_session",
    "get_db_session",
    "get_engine",
    "is_initialized",
    "init_db",
    "dispose_db",
    # Alembic utilities
    "AlembicManager",
]
