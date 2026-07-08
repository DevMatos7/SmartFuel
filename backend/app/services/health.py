"""Checagens de dependências para health detalhado (RDC-006 / RDC-007)."""

import time

import httpx
import redis.asyncio as redis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import get_logger
from app.schemas.health import (
    DetailedHealthResponse,
    ServiceHealth,
    ServicesHealthMap,
)

logger = get_logger(__name__)

HEALTH_CHECK_TIMEOUT_SECONDS = 2.0


async def build_detailed_health(version: str) -> DetailedHealthResponse:
    database = await _check_database()
    redis_status = await _check_redis()
    object_storage = await _check_minio()

    services = ServicesHealthMap(
        api=ServiceHealth(status="healthy", response_time_ms=0),
        database=database,
        redis=redis_status,
        object_storage=object_storage,
    )
    overall = _aggregate_status(services)
    return DetailedHealthResponse(status=overall, version=version, services=services)


def _aggregate_status(services: ServicesHealthMap) -> str:
    if services.database.status == "unhealthy":
        return "unhealthy"
    if services.redis.status == "unhealthy" or services.object_storage.status == "unhealthy":
        return "degraded"
    return "healthy"


async def _check_database() -> ServiceHealth:
    started = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        elapsed = _elapsed_ms(started)
        return ServiceHealth(status="healthy", response_time_ms=elapsed)
    except Exception as exc:  # noqa: BLE001
        logger.warning("database_health_failed error=%s", type(exc).__name__)
        return ServiceHealth(
            status="unhealthy",
            response_time_ms=_elapsed_ms(started),
            message="Service unavailable",
        )


async def _check_redis() -> ServiceHealth:
    started = time.perf_counter()
    try:
        client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=HEALTH_CHECK_TIMEOUT_SECONDS,
        )
        try:
            pong = await client.ping()
            if not pong:
                return ServiceHealth(
                    status="unhealthy",
                    response_time_ms=_elapsed_ms(started),
                    message="Service unavailable",
                )
            return ServiceHealth(status="healthy", response_time_ms=_elapsed_ms(started))
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_health_failed error=%s", type(exc).__name__)
        return ServiceHealth(
            status="unhealthy",
            response_time_ms=_elapsed_ms(started),
            message="Service unavailable",
        )


async def _check_minio() -> ServiceHealth:
    started = time.perf_counter()
    if not settings.minio_endpoint:
        return ServiceHealth(
            status="unhealthy",
            message="Service unavailable",
            response_time_ms=_elapsed_ms(started),
        )

    scheme = "https" if settings.minio_secure else "http"
    url = f"{scheme}://{settings.minio_endpoint}/minio/health/live"
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return ServiceHealth(status="healthy", response_time_ms=_elapsed_ms(started))
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio_health_failed error=%s", type(exc).__name__)

    return ServiceHealth(
        status="unhealthy",
        response_time_ms=_elapsed_ms(started),
        message="Service unavailable",
    )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
