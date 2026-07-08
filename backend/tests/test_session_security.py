import pytest
from httpx import AsyncClient

from factories import login


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient, admin_user) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    old_refresh = login_resp.cookies.get("refresh_token")
    assert old_refresh

    refresh_resp = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_refresh
    assert new_refresh != old_refresh


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family(client: AsyncClient, admin_user) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    old_refresh = login_resp.cookies["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.cookies["refresh_token"]

    reuse = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert reuse.status_code == 401

    blocked = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": new_refresh})
    assert blocked.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient, admin_user) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    token = login_resp.json()["access_token"]
    refresh = login_resp.cookies["refresh_token"]

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        cookies={"refresh_token": refresh},
    )
    assert logout.status_code == 200

    refresh_after = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh})
    assert refresh_after.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, db_session, org) -> None:
    from factories import create_user

    await create_user(
        db_session,
        organization_id=org.id,
        email="inativo@test.com",
        role_codes=["CONSULTA"],
        has_all_stations_access=False,
        station_ids=[],
        active=False,
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inativo@test.com", "password": "SenhaSegura123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_inactive_organization_blocks_login(client: AsyncClient, db_session) -> None:
    from factories import create_organization, create_user

    org = await create_organization(db_session, cnpj="99888777000166")
    org.active = False
    await create_user(
        db_session,
        organization_id=org.id,
        email=f"orginativa-{org.id}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": f"orginativa-{org.id}@test.com", "password": "SenhaSegura123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_password_change_revokes_previous_sessions(client: AsyncClient, admin_user) -> None:
    first_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "SenhaSegura123"},
    )
    old_token = first_login.json()["access_token"]
    old_refresh = first_login.cookies["refresh_token"]

    token, _ = await login(client, "admin@test.com", "SenhaSegura123")
    change = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "SenhaSegura123",
            "new_password": "NovaSenha456",
            "new_password_confirmation": "NovaSenha456",
        },
    )
    assert change.status_code == 200

    me_old = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me_old.status_code == 401

    refresh_old = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert refresh_old.status_code == 401
