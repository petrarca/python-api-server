"""Alembic utility functions for database schema management.

Provides reusable functionality for:
- Alembic configuration and version detection
"""

import os
from typing import Any

import alembic.command
import alembic.config
from alembic.script import ScriptDirectory
from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .connection import borrow_db_session


class AlembicManager:
    """Centralized alembic operations manager.

    Provides utilities for schema validation, migration detection,
    and migration execution without being tied to the check framework.
    """

    def __init__(self):
        """Initialize alembic configuration."""
        self.alembic_cfg = None
        self._init_alembic_config()

    def _init_alembic_config(self) -> None:
        """Initialize alembic configuration.

        Searches for alembic.ini in the following order:
        1. Current working directory
        2. Server package root (where this module is installed)

        Also sets the script_location to absolute path so migrations work from any directory.
        """
        try:
            # Try current working directory first
            alembic_ini_path = os.path.join(os.getcwd(), "alembic.ini")
            server_root = os.getcwd()

            # If not found, try the server package root
            if not os.path.exists(alembic_ini_path):
                # Get the package root (3 levels up from this file: database/ -> api_server/ -> src/ -> server/)
                server_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                alembic_ini_path = os.path.join(server_root, "alembic.ini")

            if not os.path.exists(alembic_ini_path):
                logger.error("Alembic configuration file not found in cwd or package root")
                self.alembic_cfg = None
                return

            logger.trace(f"Loading alembic configuration from: {alembic_ini_path}")
            self.alembic_cfg = alembic.config.Config(alembic_ini_path)

            # Override script_location with absolute path so it works from any directory
            migrations_path = os.path.join(server_root, "migrations")
            if os.path.exists(migrations_path):
                self.alembic_cfg.set_main_option("script_location", migrations_path)
                logger.trace(f"Set migrations path to: {migrations_path}")
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Failed to initialize alembic configuration: {str(e)}")
            self.alembic_cfg = None

    def get_current_revision(self) -> str | None:
        """Get current alembic revision from database."""
        if not self.alembic_cfg:
            logger.error("Alembic configuration not initialized")
            return None

        with borrow_db_session() as session:
            try:
                result = session.exec(text("SELECT version_num FROM alembic_version LIMIT 1"))
                current_rev = result.one_or_none()

                # Extract the actual value from Row object if needed
                if current_rev is not None:
                    # Handle different result formats safely
                    if isinstance(current_rev, tuple) and len(current_rev) == 1:
                        current_rev = current_rev[0]
                    elif hasattr(current_rev, "version_num"):
                        current_rev = current_rev.version_num
                    elif hasattr(current_rev, "_mapping"):
                        current_rev = current_rev._mapping.get("version_num")

                logger.trace(f"Current database revision: {current_rev}")
                return current_rev
            except (SQLAlchemyError, ValueError, RuntimeError, AttributeError) as e:
                logger.error(f"Failed to get current revision: {str(e)}")
                return None

    def get_head_revision(self) -> str:
        """Get head revision from alembic scripts."""
        if not self.alembic_cfg:
            logger.error("Alembic configuration not initialized")
            return ""

        try:
            script_directory = ScriptDirectory.from_config(self.alembic_cfg)
            head_rev = script_directory.get_current_head()
            logger.trace(f"Head revision from scripts: {head_rev}")
            return head_rev or ""
        except (OSError, ValueError, RuntimeError, AttributeError) as e:
            logger.error(f"Failed to get head revision: {str(e)}")
            return ""

    def needs_migration(self) -> bool:
        """Check if database needs migration."""
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()

        if not current_rev:
            logger.warning("No current revision found - database may not be initialized")
            return True

        if not head_rev:
            logger.warning("No head revision found - no alembic scripts available")
            return False

        needs_migration = current_rev != head_rev
        if needs_migration:
            logger.info(f"Migration needed: current={current_rev}, head={head_rev}")
        else:
            logger.info(f"Database up to date: {current_rev}")

        return needs_migration

    def perform_migration(self, target: str = "head") -> bool:
        """Execute database migration to specified target.

        Args:
            target: Migration target (default: "head")

        Returns:
            True if migration successful, False otherwise
        """
        if not self.alembic_cfg:
            logger.error("Alembic configuration not initialized")
            return False

        try:
            logger.info(f"Starting database migration to '{target}'")
            alembic.command.upgrade(self.alembic_cfg, target)
            logger.info(f"Database migration to '{target}' completed successfully")
            return True
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.error(f"Migration failed: {str(e)}")
            return False

    def validate_schema_state(self) -> tuple[str, dict[str, Any], bool]:
        """Validate schema state without performing migrations.

        Returns:
            Tuple of (message, details, is_success) that can be used with ReadinessCheck methods
        """
        if not self.alembic_cfg:
            return ("Alembic configuration not available", {"error": "alembic_cfg is None"}, False)

        with borrow_db_session() as session:
            try:
                # Check alembic version table exists
                inspector = inspect(session.bind)
                if "alembic_version" not in inspector.get_table_names():
                    return ("Alembic version table not found", {"has_alembic_table": False}, False)

                # Get current and head revisions
                current_rev = self.get_current_revision()
                head_rev = self.get_head_revision()

                if not current_rev:
                    return (
                        "No alembic version record found",
                        {
                            "has_alembic_table": True,
                            "has_version": False,
                            "current_revision": None,
                            "head_revision": head_rev,
                            "is_latest": False,
                        },
                        False,
                    )

                # Check if current version matches head
                is_latest = current_rev == head_rev
                if is_latest:
                    return (
                        "Database schema is properly set up and at latest version",
                        {
                            "has_alembic_table": True,
                            "has_version": True,
                            "current_revision": current_rev,
                            "head_revision": head_rev,
                            "is_latest": True,
                        },
                        True,
                    )
                else:
                    return (
                        f"Database schema is out of date. Current: {current_rev}, Head: {head_rev}",
                        {
                            "has_alembic_table": True,
                            "has_version": True,
                            "current_revision": current_rev,
                            "head_revision": head_rev,
                            "is_latest": False,
                        },
                        False,
                    )

            except (OSError, ValueError, RuntimeError, AttributeError) as e:
                logger.error(f"Error checking database schema: {str(e)}")
                return (f"Error checking database schema: {str(e)}", {"error": str(e), "type": type(e).__name__}, False)
