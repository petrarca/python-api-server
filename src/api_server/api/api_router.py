"""API router initialization."""

from fastapi import APIRouter
from loguru import logger

# from api_server.api.search import router as search_router

# Create main API router
router = APIRouter()

# TODO: Replace comment with exemplary service
# router.include_router(search_router, prefix="/search")
logger.debug("API router initialized")
