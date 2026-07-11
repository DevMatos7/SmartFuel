"""Inteligência Auto Postos — API FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware
from app.schemas.health import API_SERVICE_NAME, HealthResponse

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("starting_app name=%s env=%s", settings.app_name, settings.app_env)
    yield
    logger.info("stopping_app")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_root() -> HealthResponse:
    return HealthResponse(service=API_SERVICE_NAME, version=settings.app_version)


@app.get("/health/live", response_model=HealthResponse, tags=["health"])
async def health_live_root() -> HealthResponse:
    return HealthResponse(service=API_SERVICE_NAME, version=settings.app_version)


@app.get("/health/ready", tags=["health"])
async def health_ready_root() -> dict:
    from app.services.health import build_detailed_health

    detailed = await build_detailed_health(settings.app_version)
    ready = detailed.services.database.status == "healthy"
    return {"status": "ready" if ready else "not_ready", "version": settings.app_version}


@app.get("/health/dependencies", tags=["health"])
async def health_dependencies_root() -> dict:
    from app.services.health import build_detailed_health

    detailed = await build_detailed_health(settings.app_version)
    return {
        "postgresql": detailed.services.database.status,
        "redis": detailed.services.redis.status,
        "minio": detailed.services.object_storage.status,
        "xpert": "degraded/unsafe",
        "overall": detailed.status,
    }