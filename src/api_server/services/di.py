"""Dependency injection setup module.

This module provides centralized service registration for both
FastAPI server and CLI applications.
"""

from loguru import logger

from api_server.services.address_service import AddressService, get_address_service
from api_server.services.health_check_service import HealthCheckService, get_health_check_service
from api_server.services.patient_service import PatientService, get_patient_service
from api_server.services.registry import ServiceRegistry


def register_core_services(registry: ServiceRegistry) -> None:
    """Register core services in the service registry.

    Core services are registered as factories because they're lightweight
    and their get_*_service() functions already provide singleton behavior via @lru_cache.
    This allows lazy initialization and follows the standard service pattern.

    Args:
        registry: Service registry instance to register services in
    """
    logger.debug("Registering core services in DI container")

    # Register core service factories
    registry.register_factory(HealthCheckService, get_health_check_service)


def register_app_services(registry: ServiceRegistry) -> None:
    """Register application-specific services in the service registry.

    Application services are the main business logic services for the API.
    These are registered as factories because they're lightweight
    and their get_*_service() functions already provide singleton behavior via @lru_cache.

    Args:
        registry: Service registry instance to register services in
    """
    logger.debug("Registering application services in DI container")

    # Register application service factories
    registry.register_factory(PatientService, get_patient_service)
    registry.register_factory(AddressService, get_address_service)


def register_all_services(registry: ServiceRegistry) -> None:
    """Register all services in the service registry.

    This is a convenience function that registers both core and application services.

    Args:
        registry: Service registry instance to register services in
    """
    register_core_services(registry)
    register_app_services(registry)
