"""Checagens leves de dependências para health detalhado."""

import redis.asyncio as redis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_dependencies() -> dict[str, str]:
    return {
        "database": await _check_database(),
        "redis": await _check_redis(),
        "minio": await _check_minio(),
    }


async def _check_database() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 — health nunca deve falhar o request
        logger.warning("database_health_failed", extra={"error": str(exc)})
        return "unavailable"


async def _check_redis() -> str:
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            pong = await client.ping()
            return "ok" if pong else "unavailable"
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_health_failed", extra={"error": str(exc)})
        return "unavailable"


async def _check_minio() -> str:
    """Na Sprint 0 apenas reportamos configuração; conexão profunda nas sprints de evidência."""
    if settings.minio_endpoint and settings.minio_access_key:
        return "configured"
    return "unconfigured"
