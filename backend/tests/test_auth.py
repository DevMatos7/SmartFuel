import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_login_valid(client: AsyncClient, admin_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "admin@test.com"
    assert "refresh_token" in response.cookies or response.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, admin_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "errada"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, admin_user: User) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    token = login.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert "ADMIN" in data["roles"]
    assert "organizations.read" in data["permissions"]
