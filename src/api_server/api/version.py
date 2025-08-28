"""Version API endpoint."""

from fastapi import APIRouter

from api_server.utils.version import VersionInfo, get_version

# Create router
router = APIRouter(tags=["System"])


@router.get("", response_model=VersionInfo)
async def get_version_endpoint() -> VersionInfo:
    """Get the version information.

    Returns:
        VersionInfo: The version information.
    """
    return get_version()
