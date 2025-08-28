"""Version utility module for API server."""

import re
import sys

from loguru import logger
from pydantic import BaseModel


class VersionInfo(BaseModel):
    """Version information model."""

    full_version: str
    version: str
    post_count: str | None = None
    git_commit: str | None = None
    is_dirty: bool = False
    build_timestamp: str | None = None


def get_version() -> VersionInfo:
    """Get the version information with fallback for development.

    Returns:
        VersionInfo model containing:
            - version: base version string (e.g., "0.1.0")
            - full_version: full version string (e.g., "0.1.0.post5+gae22386.dirty.2025-03-23T10:57:26Z")
            - post_count: post count (e.g., "5" or None if not available)
            - git_commit: git commit (e.g., "ae22386" or None if not available)
            - is_dirty: dirty flag (True if the working directory had uncommitted changes)
            - build_timestamp: build timestamp (e.g., "2025-03-23T10:57:26Z" or None if not available)
    """
    try:
        logger.trace(f"Python path: {sys.path}")
        logger.trace("Attempting to import version from api_server.__version__")
        # The variable in __version__.py is named __version__, not version
        from api_server.__version__ import __version__ as full_version

        logger.info(f"Successfully imported version: {full_version}")

        # Parse the version string into components
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(full_version)
    except ImportError as e:
        # Fallback for development when __version__.py might not exist yet
        logger.warning(f"Could not import __version__.py: {e}, using default version")
        full_version = "0.1.0-dev"
        base_version = full_version
        post_count = None
        git_commit = None
        is_dirty = False
        build_timestamp = None

    return VersionInfo(
        version=base_version,
        full_version=full_version,
        post_count=post_count,
        git_commit=git_commit,
        is_dirty=is_dirty,
        build_timestamp=build_timestamp,
    )


def parse_version(version: str) -> tuple[str, str | None, str | None, bool, str | None]:
    """Parse version string into its components.

    Args:
        version: Version string to parse (e.g., "0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z")

    Returns:
        tuple containing:
            - base version (e.g., "0.1.0")
            - post count (e.g., "11" or None if not available)
            - git commit (e.g., "a524f7b" or None if not available)
            - dirty flag (True if the working directory had uncommitted changes)
            - build timestamp (e.g., "2025-03-23T21:41:10Z" or None if not available)
    """
    # Extract base version (before any post or git info)
    base_version_match = re.match(r"^(\d+\.\d+\.\d+)", version)
    base_version = base_version_match.group(1) if base_version_match else version

    # Extract post count if available
    post_match = re.search(r"\.post(\d+)", version)
    post_count = post_match.group(1) if post_match else None

    # Extract git commit if available
    git_match = re.search(r"\+g([a-f0-9]+)", version)
    git_commit = git_match.group(1) if git_match else None

    # Check if dirty flag is present
    is_dirty = ".dirty" in version

    # Extract build timestamp if available
    timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$", version)
    build_timestamp = timestamp_match.group(1) if timestamp_match else None

    return base_version, post_count, git_commit, is_dirty, build_timestamp


def extract_build_timestamp(version: str) -> str | None:
    """Extract build timestamp from version string if available.

    The version format includes timestamp in ISO 8601 format at the end
    Format is typically: 0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z

    Args:
        version: Version string to extract timestamp from

    Returns:
        Build timestamp string or None if not available
    """
    timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$", version)
    return timestamp_match.group(1) if timestamp_match else None
