from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import DetailedHealthResponse, HealthResponse
from app.services.health import check_dependencies

router = APIRouter()


@router.get("/health", response_model=DetailedHealthResponse)
async def health_v1() -> DetailedHealthResponse:
    deps = await check_dependencies()
    overall = "ok" if deps["database"] == "ok" else "degraded"
    return DetailedHealthResponse(
        status=overall,
        service="api-v1",
        version=settings.app_version,
        environment=settings.app_env,
        database=deps["database"],
        redis=deps["redis"],
        minio=deps["minio"],
    )


@router.get("/health/live", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    return HealthResponse(status="ok", service="api-v1", version=settings.app_version)
