from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_root(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "backend"
    assert "version" in payload


@pytest.mark.asyncio
async def test_health_v1_live(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_v1_detailed(client: AsyncClient) -> None:
    with patch(
        "app.api.v1.health.check_dependencies",
        new=AsyncMock(
            return_value={
                "database": "ok",
                "redis": "ok",
                "minio": "configured",
            }
        ),
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "api-v1"
    assert payload["database"] == "ok"
    assert payload["status"] == "ok"
