from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.health import DetailedHealthResponse, ServiceHealth, ServicesHealthMap


def healthy_services() -> ServicesHealthMap:
    item = ServiceHealth(status="healthy", response_time_ms=1)
    return ServicesHealthMap(api=item, database=item, redis=item, object_storage=item)


@pytest.mark.asyncio
async def test_health_root(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "inteligencia-auto-postos-api"
    assert payload["version"] == "0.1.0"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_health_v1_live(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_v1_detailed_healthy(client: AsyncClient) -> None:
    with patch(
        "app.api.v1.health.build_detailed_health",
        new=AsyncMock(
            return_value=DetailedHealthResponse(
                status="healthy",
                version="0.1.0",
                services=healthy_services(),
            )
        ),
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["services"]["database"]["status"] == "healthy"
    assert "response_time_ms" in payload["services"]["redis"]


@pytest.mark.asyncio
async def test_health_database_unavailable(client: AsyncClient) -> None:
    services = healthy_services()
    services = services.model_copy(
        update={"database": ServiceHealth(status="unhealthy", message="Service unavailable")}
    )
    with patch(
        "app.api.v1.health.build_detailed_health",
        new=AsyncMock(
            return_value=DetailedHealthResponse(
                status="unhealthy",
                version="0.1.0",
                services=services,
            )
        ),
    ):
        response = await client.get("/api/v1/health")

    payload = response.json()
    assert payload["status"] == "unhealthy"
    assert payload["services"]["database"]["status"] == "unhealthy"
    body = response.text.lower()
    assert "password" not in body
    assert "postgresql" not in body


@pytest.mark.asyncio
async def test_health_redis_unavailable_degraded(client: AsyncClient) -> None:
    services = healthy_services()
    services = services.model_copy(
        update={"redis": ServiceHealth(status="unhealthy", message="Service unavailable")}
    )
    with patch(
        "app.api.v1.health.build_detailed_health",
        new=AsyncMock(
            return_value=DetailedHealthResponse(
                status="degraded",
                version="0.1.0",
                services=services,
            )
        ),
    ):
        response = await client.get("/api/v1/health")

    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["services"]["redis"]["message"] == "Service unavailable"


@pytest.mark.asyncio
async def test_health_minio_unavailable_degraded(client: AsyncClient) -> None:
    services = healthy_services()
    services = services.model_copy(
        update={
            "object_storage": ServiceHealth(status="unhealthy", message="Service unavailable")
        }
    )
    with patch(
        "app.api.v1.health.build_detailed_health",
        new=AsyncMock(
            return_value=DetailedHealthResponse(
                status="degraded",
                version="0.1.0",
                services=services,
            )
        ),
    ):
        response = await client.get("/api/v1/health")

    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["services"]["object_storage"]["status"] == "unhealthy"
