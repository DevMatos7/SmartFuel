import pytest
from httpx import AsyncClient

from factories import login


@pytest.mark.asyncio
async def test_consulta_cannot_create_station(client: AsyncClient, consulta_user, org, branch_station) -> None:
    token, _ = await login(client, "consulta@test.com", "SenhaSegura123")
    response = await client.post(
        "/api/v1/stations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organization_id": str(org.id),
            "station_type": "BRANCH",
            "corporate_name": "Novo LTDA",
            "trade_name": "Novo",
            "cnpj": "11222333000505",
            "brand_type": "WHITE_LABEL",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_station_access_denied_for_unlinked_station(
    client: AsyncClient, consulta_user, headquarters, branch_station
) -> None:
    token, _ = await login(client, "consulta@test.com", "SenhaSegura123")
    response = await client.get(
        f"/api/v1/stations/{headquarters.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_permission_removed_during_session(
    client: AsyncClient, session_factory, consulta_user, branch_station, admin_user, auth_headers
) -> None:
    token, _ = await login(client, "consulta@test.com", "SenhaSegura123")
    ok = await client.get("/api/v1/stations", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    async with session_factory() as session:
        from sqlalchemy import delete
        from app.models.user import UserStation

        await session.execute(
            delete(UserStation).where(
                UserStation.user_id == consulta_user.id,
                UserStation.station_id == branch_station.id,
            )
        )
        await session.commit()

    denied = await client.get(
        f"/api/v1/stations/{branch_station.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403
