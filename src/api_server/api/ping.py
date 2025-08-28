"""Ping API endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["System"])


class PingResponse(BaseModel):
    """Ping response model."""

    ping: str = "pong"


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    """
    Simple ping endpoint that returns a pong response.

    This endpoint is used for basic connectivity testing and does not require
    any database access or authentication.

    Returns:
        PingResponse: A simple response with {"ping": "pong"}
    """
    return PingResponse()
