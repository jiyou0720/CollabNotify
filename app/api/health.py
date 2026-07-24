"""Health-check API endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_health_status
from app.schemas.response import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check application health",
)
async def health_check(
    health_status: Annotated[str, Depends(get_health_status)],
) -> HealthResponse:
    """Return a lightweight process health response."""
    return HealthResponse(status=health_status)
