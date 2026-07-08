import pytest
from httpx import AsyncClient

from app.utils.sanitize import sanitize_for_audit


def test_sanitize_removes_nested_secrets() -> None:
    payload = {
        "email": "a@b.com",
        "nested": {"password": "secret", "access_token": "jwt"},
        "metadata": {"refresh_token": "rt"},
    }
    sanitized = sanitize_for_audit(payload)
    assert sanitized["nested"]["password"] == "***"
    assert sanitized["nested"]["access_token"] == "***"
    assert sanitized["metadata"]["refresh_token"] == "***"
    assert sanitized["email"] == "a@b.com"


@pytest.mark.asyncio
async def test_create_station_generates_audit_without_secrets(
    client: AsyncClient, org, auth_headers
) -> None:
    await client.post(
        "/api/v1/stations",
        headers=auth_headers,
        json={
            "organization_id": str(org.id),
            "station_type": "BRANCH",
            "corporate_name": "Audit LTDA",
            "trade_name": "Audit Posto",
            "cnpj": "11222333000858",
            "brand_type": "WHITE_LABEL",
        },
    )

    logs = await client.get("/api/v1/audit-logs?entity_type=station", headers=auth_headers)
    assert logs.status_code == 200
    item = logs.json()["items"][0]
    assert item["after_data"] is not None
    assert "password" not in str(item["after_data"])
    assert "token" not in str(item["after_data"]).lower() or "***" in str(item["after_data"])
