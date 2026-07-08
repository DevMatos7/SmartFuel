import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_rate_limit_returns_429(client: AsyncClient, admin_user, monkeypatch) -> None:
    import redis.asyncio as redis

    from app.services.rate_limit import login_rate_limiter

    monkeypatch.setattr(settings, "login_rate_limit", 2)
    monkeypatch.setattr(settings, "login_rate_window_seconds", 60)
    login_rate_limiter._memory.clear()

    def fail_redis(*args, **kwargs):
        raise redis.ConnectionError("redis indisponível")

    monkeypatch.setattr(redis, "from_url", fail_redis)

    for _ in range(2):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "wrong"},
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
