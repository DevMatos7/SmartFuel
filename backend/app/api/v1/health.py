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


@router.get("/health/ready")
async def health_ready() -> dict:
    detailed = await build_detailed_health(settings.app_version)
    ready = detailed.services.database.status == "healthy"
    return {
        "status": "ready" if ready else "not_ready",
        "version": settings.app_version,
        "database": detailed.services.database.status,
        "redis": detailed.services.redis.status,
        "object_storage": detailed.services.object_storage.status,
        "note": "XPERT não bloqueia readiness da API; ver /health/dependencies.",
    }


@router.get("/health/dependencies")
async def health_dependencies() -> dict:
    detailed = await build_detailed_health(settings.app_version)
    return {
        "postgresql": detailed.services.database.status,
        "redis": detailed.services.redis.status,
        "minio": detailed.services.object_storage.status,
        "xpert": {
            "status": "degraded/unsafe",
            "security_status": "UNSAFE",
            "privileged_user": "sa",
            "production_blocked": True,
            "scheduler_blocked": True,
            "read_only": True,
        },
        "overall": detailed.status,
    }
