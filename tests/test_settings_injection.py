"""Tests for Settings integration and service injection."""

from api_server.services.address_service import AddressService, get_address_service
from api_server.settings import Settings, get_settings


def test_get_settings_returns_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    assert isinstance(s1, Settings)


def test_address_service_uses_settings_singleton():
    settings = get_settings()
    service = get_address_service()
    assert isinstance(service, AddressService)
    assert service.settings is settings


def test_address_service_custom_settings():
    custom = Settings(host="127.0.0.1", port=9999)
    service = AddressService(custom)
    assert service.settings is custom
    assert service.settings.port == 9999
