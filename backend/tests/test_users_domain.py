import pytest
from httpx import AsyncClient

from factories import create_user


@pytest.mark.asyncio
async def test_email_case_insensitive_duplicate(
    client: AsyncClient, org, branch_station, auth_headers
) -> None:
    first = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "User A",
            "email": "usuario@empresa.com",
            "temporary_password": "SenhaSegura123",
            "role_codes": ["CONSULTA"],
            "station_ids": [str(branch_station.id)],
            "has_all_stations_access": False,
        },
    )
    assert first.status_code == 201

    second = await client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "name": "User B",
                "email": "USUARIO@EMPRESA.COM",
                "temporary_password": "SenhaSegura123",
                "role_codes": ["CONSULTA"],
                "station_ids": [],
                "has_all_stations_access": False,
            },
        )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_user_without_station_rejected(client: AsyncClient, org, branch_station, auth_headers) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Sem Posto",
            "email": "semposto@test.com",
            "temporary_password": "SenhaSegura123",
            "role_codes": ["CONSULTA"],
            "station_ids": [],
            "has_all_stations_access": False,
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_has_all_stations_access_only_for_admin(
    client: AsyncClient, org, branch_station, auth_headers
) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Gestor Total",
            "email": "gestor@test.com",
            "temporary_password": "SenhaSegura123",
            "role_codes": ["GESTOR"],
            "station_ids": [str(branch_station.id)],
            "has_all_stations_access": True,
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_stations(client: AsyncClient, session_factory, org, branch_station, headquarters, auth_headers) -> None:
    async with session_factory() as session:
        user = await create_user(
            session,
            organization_id=org.id,
            email="vinculo@test.com",
            role_codes=["CONSULTA"],
            station_ids=[branch_station.id],
        )
        await session.commit()
        user_id = user.id

    response = await client.put(
        f"/api/v1/users/{user_id}/stations",
        headers=auth_headers,
        json={
            "station_ids": [str(branch_station.id), str(headquarters.id)],
            "has_all_stations_access": False,
        },
    )
    assert response.status_code == 200

    detail = await client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert len(detail.json()["station_ids"]) == 2
