import pytest
from httpx import AsyncClient

from factories import create_user, login


@pytest.mark.asyncio
async def test_must_change_password_blocks_stations(client: AsyncClient, db_session, org) -> None:
    await create_user(
        db_session,
        organization_id=org.id,
        email="troca@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
        must_change_password=True,
    )
    await db_session.flush()

    token, _ = await login(client, "troca@test.com", "SenhaSegura123")
    response = await client.get("/api/v1/stations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MUST_CHANGE_PASSWORD"


@pytest.mark.asyncio
async def test_must_change_password_allows_me_and_change(client: AsyncClient, db_session, org) -> None:
    await create_user(
        db_session,
        organization_id=org.id,
        email="troca2@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
        must_change_password=True,
    )
    await db_session.flush()

    token, _ = await login(client, "troca2@test.com", "SenhaSegura123")

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    change = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "SenhaSegura123",
            "new_password": "NovaSenha789",
            "new_password_confirmation": "NovaSenha789",
        },
    )
    assert change.status_code == 200

    stations = await client.get(
        "/api/v1/stations",
        headers={"Authorization": f"Bearer {change.json()['access_token']}"},
    )
    assert stations.status_code == 200


@pytest.mark.asyncio
async def test_must_change_password_blocks_users(client: AsyncClient, db_session, org) -> None:
    await create_user(
        db_session,
        organization_id=org.id,
        email="troca3@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
        must_change_password=True,
    )
    await db_session.flush()

    token, _ = await login(client, "troca3@test.com", "SenhaSegura123")
    response = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MUST_CHANGE_PASSWORD"
