"""Application configuration using Pydantic Settings.

This module centralizes runtime configuration for the API server. Values can
be provided via environment variables (preferred) or fall back to the defaults
below. A ``Settings`` instance is intended to be retrieved via ``get_settings``
which caches the object for reuse across the process.

Environment variable prefix: ``API_SERVER_`` (e.g. ``API_SERVER_HOST``).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings.

    Attributes map directly to environment variables using the ``API_SERVER_``
    prefix (case-insensitive). For example, ``host`` <- ``API_SERVER_HOST``.
    """

    # Server settings
    # These settings control the behavior of the API server itself.
    host: str = Field(
        default="0.0.0.0",
        description="Host interface to bind the server",
    )  # fmt: skip
    port: int = Field(
        default=8080,
        description="Server port",
    )  # fmt: skip
    log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Application log level",
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload in development",
    )  # fmt: skip
    sql_log: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )  # fmt: skip
    database_url: str | None = Field(
        default=None,
        description="Database connection string",
    )  # fmt: skip
    check_only: bool = Field(
        default=False,
        description="Run readiness checks only, then exit (without starting server)",
    )  # fmt: skip
    profiles: str | None = Field(
        default=None,
        description="Server profiles: rest, graphql, or comma-separated combination. Empty/None enables all.",
    )  # fmt: skip

    # Additional future settings can be appended here.

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str | None) -> str:
        """Normalize and validate log level."""
        if v is None:
            return "INFO"

        # Normalize to uppercase
        v_upper = str(v).upper()

        # Validate against allowed values
        allowed = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR"}
        if v_upper not in allowed:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {', '.join(sorted(allowed))}")

        return v_upper

    model_config = SettingsConfigDict(
        env_prefix="API_SERVER_",  # Prefix for env vars
        case_sensitive=False,
        extra="ignore",  # Ignore unexpected env vars
        env_file=".env",  # Optional .env loading (if present)
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached ``Settings`` instance.

    The first invocation reads environment variables / .env file; subsequent
    calls reuse the same object to ensure consistent config.
    """

    return Settings()


__all__ = ["Settings", "get_settings"]
