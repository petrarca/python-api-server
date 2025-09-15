"""Application configuration using Pydantic Settings.

This module centralizes runtime configuration for the API server. Values can
be provided via environment variables (preferred) or fall back to the defaults
below. A ``Settings`` instance is intended to be retrieved via ``get_settings``
which caches the object for reuse across the process.

Environment variable prefix: ``API_SERVER_`` (e.g. ``API_SERVER_HOST``).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings.

    Attributes map directly to environment variables using the ``API_SERVER_``
    prefix (case-insensitive). For example, ``host`` <- ``API_SERVER_HOST``.
    """

    host: str = Field(default="0.0.0.0", description="Host interface to bind the server")
    port: int = Field(default=8080, description="Port the server listens on")
    log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", description="Application log level")
    sql_log: bool = Field(default=False, description="Enable SQL query logging")
    reload: bool = Field(default=True, description="Enable auto-reload in development")

    # Additional future settings (DB URL etc.) can be appended here.

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
