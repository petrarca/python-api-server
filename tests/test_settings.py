"""Tests for api_server.config.Settings behavior."""

from typing import Any

import pytest

from api_server.settings import Settings, get_settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch):
    """Defaults should be stable even if external env or .env sets values.

    We explicitly delete both upper & lower case variants and bypass .env loading
    by passing `_env_file=None`.
    """
    for var in [
        "API_SERVER_HOST",
        "API_SERVER_PORT",
        "API_SERVER_LOG_LEVEL",
        "API_SERVER_SQL_LOG",
        "API_SERVER_RELOAD",
        "api_server_host",
        "api_server_port",
    ]:
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)  # ignore project .env file if present
    assert s.host == "0.0.0.0"
    assert s.port == 8080
    assert s.log_level == "INFO"
    assert s.sql_log is False
    assert s.reload is False


def test_env_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("API_SERVER_PORT", "9090")
    monkeypatch.setenv("API_SERVER_SQL_LOG", "true")
    monkeypatch.setenv("API_SERVER_RELOAD", "false")
    s = Settings()  # new instance reads env
    assert s.host == "127.0.0.1"
    assert s.port == 9090
    assert s.sql_log is True
    assert s.reload is False


def test_case_insensitive_env_name(monkeypatch: pytest.MonkeyPatch):
    # lower-case variable name should still be picked up due to case_sensitive=False
    monkeypatch.setenv("api_server_host", "10.10.10.10")  # type: ignore[arg-type]
    s = Settings()
    assert s.host == "10.10.10.10"


def test_get_settings_singleton():
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_settings_cache_not_affected_by_new_env(monkeypatch: pytest.MonkeyPatch):
    # Ensure cache stability: first call caches values
    first = get_settings()
    original_host = first.host
    monkeypatch.setenv("API_SERVER_HOST", "203.0.113.5")
    second = get_settings()
    assert second is first
    assert second.host == original_host  # cache not invalidated


@pytest.mark.parametrize(
    "override,expected",
    [
        ({"host": "1.1.1.1"}, "1.1.1.1"),
        ({"port": 1234}, 1234),
    ],
)
def test_direct_instantiation_with_overrides(override: dict[str, Any], expected: Any):
    s = Settings(**override)
    # pick first and assert value
    key = next(iter(override.keys()))
    assert getattr(s, key) == expected


def test_model_dump_contains_all_core_fields():
    s = Settings()
    data = s.model_dump()
    for field in ["host", "port", "log_level", "sql_log", "reload", "database_url"]:
        assert field in data


def test_database_url_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_SERVER_DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    s = Settings()
    assert s.database_url == "postgresql+psycopg://u:p@h/db"
