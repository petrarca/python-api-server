"""API router initialization."""

from fastapi import APIRouter
from loguru import logger

from api_server.api.addresses import router as addresses_router
from api_server.api.patients import router as patients_router

# Create main API router
router = APIRouter()

# Mount API endpoints
router.include_router(patients_router, tags=["patients"])
router.include_router(addresses_router, tags=["addresses"])

logger.debug("API router initialized (patients, addresses routers mounted)")
