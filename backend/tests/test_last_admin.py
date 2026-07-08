import pytest
from httpx import AsyncClient

from factories import create_user, login


@pytest.mark.asyncio
async def test_cannot_self_deactivate(client: AsyncClient, admin_user, auth_headers) -> None:
    users = await client.get("/api/v1/users", headers=auth_headers)
    user_id = users.json()["items"][0]["id"]

    response = await client.post(
        f"/api/v1/users/{user_id}/deactivate",
        headers=auth_headers,
        json={"reason": "teste"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cannot_remove_admin_role_from_last_admin(
    client: AsyncClient, admin_user, auth_headers
) -> None:
    users = await client.get("/api/v1/users", headers=auth_headers)
    user_id = users.json()["items"][0]["id"]

    response = await client.put(
        f"/api/v1/users/{user_id}/roles",
        headers=auth_headers,
        json={"role_codes": ["GESTOR"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_ADMIN_PROTECTION"


@pytest.mark.asyncio
async def test_admin_can_deactivate_when_another_admin_exists(
    client: AsyncClient, db_session, org, admin_user, auth_headers
) -> None:
    second = await create_user(
        db_session,
        organization_id=org.id,
        email="admin2@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    await db_session.flush()
    second_id = second.id

    users = await client.get("/api/v1/users", headers=auth_headers)
    target_id = next(item["id"] for item in users.json()["items"] if item["email"] == "admin@test.com")

    token2, _ = await login(client, "admin2@test.com", "SenhaSegura123")
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = await client.post(
        f"/api/v1/users/{target_id}/deactivate",
        headers=headers2,
        json={"reason": "desligamento"},
    )
    assert response.status_code == 200

    login_blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    assert login_blocked.status_code == 401

    token2, _ = await login(client, "admin2@test.com", "SenhaSegura123")
    assert token2
