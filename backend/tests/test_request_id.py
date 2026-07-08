import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_request_id_propagated(client: AsyncClient) -> None:
    custom_id = "8c88244b-6e2e-4e98-8bfe-7fe13bcd32cc"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id
