from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import API_SERVICE_NAME, DetailedHealthResponse, HealthResponse
from app.services.health import build_detailed_health

router = APIRouter()


@router.get("/health", response_model=DetailedHealthResponse)
async def health_v1() -> DetailedHealthResponse:
    return await build_detailed_health(settings.app_version)


@router.get("/health/live", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    return HealthResponse(version=settings.app_version, service=API_SERVICE_NAME)
