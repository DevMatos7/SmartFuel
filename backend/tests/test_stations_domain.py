import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_headquarters(client: AsyncClient, org, auth_headers) -> None:
    response = await client.post(
        "/api/v1/stations",
        headers=auth_headers,
        json={
            "organization_id": str(org.id),
            "station_type": "HEADQUARTERS",
            "corporate_name": "Matriz LTDA",
            "trade_name": "Matriz Central",
            "cnpj": "11222333000262",
            "brand_type": "WHITE_LABEL",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_second_headquarters_rejected(client: AsyncClient, org, headquarters, auth_headers) -> None:
    response = await client.post(
        "/api/v1/stations",
        headers=auth_headers,
        json={
            "organization_id": str(org.id),
            "station_type": "HEADQUARTERS",
            "corporate_name": "Outra Matriz LTDA",
            "trade_name": "Outra Matriz",
            "cnpj": "11222333000696",
            "brand_type": "WHITE_LABEL",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "HEADQUARTERS_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_duplicate_cnpj_rejected(client: AsyncClient, org, headquarters, auth_headers) -> None:
    response = await client.post(
        "/api/v1/stations",
        headers=auth_headers,
        json={
            "organization_id": str(org.id),
            "station_type": "BRANCH",
            "corporate_name": "Dup LTDA",
            "trade_name": "Dup",
            "cnpj": headquarters.cnpj,
            "brand_type": "WHITE_LABEL",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CNPJ_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_branded_requires_brand_name(client: AsyncClient, org, auth_headers) -> None:
    response = await client.post(
        "/api/v1/stations",
        headers=auth_headers,
        json={
            "organization_id": str(org.id),
            "station_type": "BRANCH",
            "corporate_name": "Shell LTDA",
            "trade_name": "Shell Posto",
            "cnpj": "11222333000777",
            "brand_type": "BRANDED",
        },
    )
    assert response.status_code == 400
