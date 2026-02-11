"""Server profile configuration and parsing.

This module handles the server profile configuration which determines
which API endpoints are enabled (REST, GraphQL).
"""

from functools import lru_cache

from api_server.constants import PROFILE_GRAPHQL, PROFILE_REST


class ProfileManager:
    """Manages server profile configuration state.

    This class follows the singleton pattern to maintain active profiles
    throughout the application lifecycle.
    """

    def __init__(self):
        self._active_profiles: set[str] | None = None

    def set_active_profiles(self, profiles: set[str]) -> None:
        """Set the active profiles (called during app startup).

        Args:
            profiles: Set of active profile names
        """
        self._active_profiles = profiles

    def get_active_profiles(self) -> set[str]:
        """Get the active profiles set.

        Returns:
            Set of active profile components (REST, GraphQL, MCP)

        Note:
            If profiles haven't been set yet, returns default (all profiles).
        """
        if self._active_profiles is None:
            # Fallback: parse from settings if not yet initialized
            # Lazy import to avoid circular imports as the codebase grows
            from api_server.settings import get_settings

            settings = get_settings()
            return parse_profile(settings.profiles)
        return self._active_profiles


@lru_cache
def get_profile_manager() -> ProfileManager:
    """Get or create the singleton ProfileManager instance.

    Returns:
        The ProfileManager instance.
    """
    return ProfileManager()


def set_active_profiles(profiles: set[str]) -> None:
    """Set the active profiles (called during app startup).

    Args:
        profiles: Set of active profile names
    """
    get_profile_manager().set_active_profiles(profiles)


def get_active_profiles() -> set[str]:
    """Get the active profiles set.

    Returns:
        Set of active profile components (REST, GraphQL)

    Note:
        If profiles haven't been set yet, returns default (all profiles).
    """
    return get_profile_manager().get_active_profiles()


def parse_profile(config: str | None) -> set[str]:
    """Parse server profile configuration.

    Args:
        config: Comma-separated profile names (case-insensitive), None, or empty string.
               None or empty string enables all profiles.

    Returns:
        Set of enabled profile components in lowercase (rest, graphql)

    Raises:
        ValueError: If invalid profile component provided

    Examples:
        >>> parse_profile(None)
        {'rest', 'graphql'}
        >>> parse_profile("")
        {'rest', 'graphql'}
        >>> parse_profile("REST")
        {'rest'}
        >>> parse_profile("Rest,GraphQL")
        {'rest', 'graphql'}
    """
    valid_profiles = {PROFILE_REST, PROFILE_GRAPHQL}

    # Empty, None, or whitespace-only means all profiles enabled
    if not config or not config.strip():
        return valid_profiles

    # Parse input (case-insensitive), convert to lowercase
    profiles = {p.strip().lower() for p in config.split(",") if p.strip()}

    # Validate
    invalid = profiles - valid_profiles
    if invalid:
        raise ValueError(f"Invalid profile components: {invalid}. Valid: {', '.join(sorted(valid_profiles))}")

    return profiles


__all__ = ["parse_profile", "get_active_profiles", "set_active_profiles", "get_profile_manager"]
