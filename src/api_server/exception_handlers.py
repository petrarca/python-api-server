"""Global exception handlers for the FastAPI application.

This module contains custom exception handlers that convert
application exceptions into proper HTTP responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from api_server.exceptions import ResourceNotFoundError, VersionConflictError


async def version_conflict_handler(request: Request, exc: VersionConflictError) -> JSONResponse:
    """Handle optimistic locking conflicts.

    Returns HTTP 409 Conflict when a resource was modified by another client
    between read and update.
    """
    logger.warning("Version conflict on {}: {}", request.url.path, exc)
    return JSONResponse(
        status_code=409,
        content={
            "error": "version_conflict",
            "message": str(exc),
            "detail": {
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        },
    )


async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    """Handle missing resource lookups.

    Returns HTTP 404 Not Found when a requested resource does not exist.
    """
    logger.warning("Resource not found on {}: {}", request.url.path, exc)
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": str(exc),
            "detail": {
                "resource_type": exc.resource_type,
                "identifier": str(exc.identifier),
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers with the FastAPI app.

    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(VersionConflictError, version_conflict_handler)
    app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)
    logger.debug("Registered exception handlers")
