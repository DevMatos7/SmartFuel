"""Testes Sprint 2.1 — estabilização de cadastros mestres."""

from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import settings
from app.models.erp_product import ErpProduct
from app.models.organization import Organization
from app.models.organization_business_settings import OrganizationBusinessSettings
from app.models.product import Product
from app.models.station import Station
from factories import create_organization, seed_master_data
from db_guard import DatabaseGuardError, validate_test_database_config


def test_test_database_url_is_required(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings, "test_database_url", "")
    with pytest.raises(DatabaseGuardError, match="TEST_DATABASE_URL"):
        validate_test_database_config()


def test_test_database_url_cannot_equal_app_database(monkeypatch) -> None:
    url = "postgresql+asyncpg://u:p@localhost:5433/smartfuel_test"
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    monkeypatch.setattr(settings, "test_database_url", url)
    monkeypatch.setattr(settings, "database_url", url)
    with pytest.raises(DatabaseGuardError, match="não pode ser o mesmo"):
        validate_test_database_config()


def test_test_database_name_must_look_like_test(monkeypatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5433/production")
    monkeypatch.setattr(settings, "test_database_url", "postgresql+asyncpg://u:p@localhost:5433/production")
    monkeypatch.setattr(settings, "database_url", "postgresql+asyncpg://u:p@localhost:5432/smartfuel")
    with pytest.raises(DatabaseGuardError, match="não parece ser de testes"):
        validate_test_database_config()


@pytest.mark.asyncio
async def test_validate_test_database_config_ok(monkeypatch) -> None:
    test_url = os.environ.get("TEST_DATABASE_URL", settings.test_database_url)
    if not test_url:
        pytest.skip("TEST_DATABASE_URL não configurada neste ambiente")
    async_url, sync_url = validate_test_database_config()
    assert "_test" in async_url or os.environ.get("TEST_DATABASE_ALLOW_UNSAFE")
    assert sync_url.startswith("postgresql+psycopg://")


@pytest.mark.asyncio
async def test_bootstrap_new_organization_idempotent(db_session) -> None:
    org = await create_organization(db_session, cnpj="99888777000155")
    await db_session.flush()

    first = await seed_master_data(db_session, org.id)
    await db_session.flush()
    second = await seed_master_data(db_session, org.id)
    await db_session.flush()

    products = await db_session.execute(
        select(func.count()).select_from(Product).where(Product.organization_id == org.id)
    )
    settings_count = await db_session.execute(
        select(func.count())
        .select_from(OrganizationBusinessSettings)
        .where(OrganizationBusinessSettings.organization_id == org.id)
    )

    assert first["products"] == 6
    assert second["products"] == 0
    assert products.scalar_one() == 6
    assert settings_count.scalar_one() == 1


@pytest.mark.asyncio
async def test_organization_business_settings_defaults(
    client: AsyncClient, auth_headers, org: Organization
) -> None:
    response = await client.get("/api/v1/organization-business-settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["default_supplier_allowed"] is False
    assert Decimal(data["default_minimum_volume_liters"]) == Decimal("5000.000")


@pytest.mark.asyncio
async def test_organization_business_settings_update_and_audit(
    client: AsyncClient, auth_headers, org: Organization
) -> None:
    patch = await client.patch(
        "/api/v1/organization-business-settings",
        headers=auth_headers,
        json={"default_supplier_allowed": True, "default_minimum_volume_liters": "6000.000"},
    )
    assert patch.status_code == 200
    assert patch.json()["default_supplier_allowed"] is True

    audit = await client.get(
        "/api/v1/audit-logs",
        headers=auth_headers,
        params={"entity_type": "organization_business_settings", "page_size": 5},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


@pytest.mark.asyncio
async def test_effective_rule_uses_organization_default(
    client: AsyncClient,
    auth_headers,
    seeded_org,
    branch_station: Station,
    db_session,
) -> None:
    distributor_resp = await client.post(
        "/api/v1/distributors",
        headers=auth_headers,
        json={
            "internal_code": "D-DEF",
            "corporate_name": "Distribuidora Default LTDA",
            "trade_name": "Distribuidora Default",
            "cnpj": "11222333000424",
        },
    )
    distributor_id = distributor_resp.json()["id"]

    products = await client.get("/api/v1/products", headers=auth_headers, params={"page_size": 1})
    product_id = products.json()["items"][0]["id"]

    await client.patch(
        "/api/v1/organization-business-settings",
        headers=auth_headers,
        json={"default_supplier_allowed": True},
    )

    effective = await client.get(
        "/api/v1/station-supplier-rules/effective",
        headers=auth_headers,
        params={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "product_id": product_id,
            "reference_date": date.today().isoformat(),
        },
    )
    assert effective.status_code == 200
    assert effective.json()["rule_source"] == "ORGANIZATION_DEFAULT"
    assert effective.json()["allowed"] is True


def _build_erp_products_csv(rows: list[dict[str, str]]) -> bytes:
    headers = [
        "erp_product_id",
        "erp_product_code",
        "erp_description",
        "erp_unit",
        "erp_group_id",
        "erp_group_name",
        "erp_subgroup_id",
        "erp_subgroup_name",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    return buffer.getvalue().encode("utf-8-sig")


@pytest.mark.asyncio
async def test_import_preview_does_not_persist_erp_products(
    client: AsyncClient,
    auth_headers,
    branch_station: Station,
    db_session,
) -> None:
    before = await db_session.execute(select(func.count()).select_from(ErpProduct))
    count_before = before.scalar_one()

    content = _build_erp_products_csv([{"erp_product_id": "PREVIEW-1", "erp_description": "Teste preview"}])
    upload = await client.post(
        "/api/v1/master-data-imports/erp-products",
        headers=auth_headers,
        data={"station_id": str(branch_station.id)},
        files={"file": ("preview.csv", content, "text/csv")},
    )
    assert upload.status_code == 201

    after = await db_session.execute(select(func.count()).select_from(ErpProduct))
    assert after.scalar_one() == count_before

    confirm = await client.post(
        f"/api/v1/master-data-imports/{upload.json()['id']}/confirm",
        headers=auth_headers,
    )
    assert confirm.status_code == 200

    after_confirm = await db_session.execute(select(func.count()).select_from(ErpProduct))
    assert after_confirm.scalar_one() == count_before + 1
