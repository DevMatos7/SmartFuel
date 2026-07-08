"""Testes de aceitação Sprint 2 — cadastros mestres."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.erp_product import ErpProduct
from app.models.organization import Organization
from app.models.product import Product
from app.models.station import Station
from app.models.user import User
from factories import create_user, login, seed_master_data


# --- Helpers ---


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def _upload_erp_products_csv(
    client: AsyncClient,
    headers: dict[str, str],
    station_id,
    rows: list[dict[str, str]],
    *,
    filename: str = "erp_products.csv",
):
    content = _build_erp_products_csv(rows)
    return await client.post(
        "/api/v1/master-data-imports/erp-products",
        headers=headers,
        data={"station_id": str(station_id)},
        files={"file": (filename, content, "text/csv")},
    )


async def _confirm_import(client: AsyncClient, headers: dict[str, str], job_id):
    return await client.post(f"/api/v1/master-data-imports/{job_id}/confirm", headers=headers)


async def _import_erp_products(
    client: AsyncClient,
    headers: dict[str, str],
    station_id,
    rows: list[dict[str, str]],
):
    upload = await _upload_erp_products_csv(client, headers, station_id, rows)
    assert upload.status_code == 201, upload.text
    job_id = upload.json()["id"]
    confirm = await _confirm_import(client, headers, job_id)
    assert confirm.status_code == 200, confirm.text
    return upload.json(), confirm.json()


async def _get_seeded_product_id(client: AsyncClient, headers: dict[str, str], code: str) -> str:
    response = await client.get("/api/v1/products", headers=headers, params={"search": code})
    assert response.status_code == 200
    items = response.json()["items"]
    match = next((p for p in items if p["code"] == code), None)
    assert match is not None, f"Produto {code} não encontrado"
    return match["id"]


async def _create_distributor(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    internal_code: str = "DIST-01",
    cnpj: str = "11222333000858",
    trade_name: str = "Distribuidora Teste",
):
    return await client.post(
        "/api/v1/distributors",
        headers=headers,
        json={
            "internal_code": internal_code,
            "corporate_name": f"{trade_name} LTDA",
            "trade_name": trade_name,
            "cnpj": cnpj,
        },
    )


@pytest.fixture
async def financeiro_user(db_session, org: Organization, branch_station: Station) -> User:
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="financeiro@test.com",
        role_codes=["FINANCEIRO"],
        station_ids=[branch_station.id],
    )
    await db_session.flush()
    return user


@pytest.fixture
async def comprador_user(db_session, org: Organization, branch_station: Station) -> User:
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="comprador@test.com",
        role_codes=["COMPRADOR"],
        station_ids=[branch_station.id],
    )
    await db_session.flush()
    return user


@pytest.fixture
async def financeiro_headers(client: AsyncClient, financeiro_user: User) -> dict[str, str]:
    token, _ = await login(client, "financeiro@test.com", "SenhaSegura123")
    return _auth(token)


@pytest.fixture
async def comprador_headers(client: AsyncClient, comprador_user: User) -> dict[str, str]:
    token, _ = await login(client, "comprador@test.com", "SenhaSegura123")
    return _auth(token)


@pytest.fixture
async def consulta_headers(client: AsyncClient, consulta_user: User) -> dict[str, str]:
    token, _ = await login(client, "consulta@test.com", "SenhaSegura123")
    return _auth(token)


# --- Product seed & CRUD ---


@pytest.mark.asyncio
async def test_product_seed_idempotent_six_products(
    db_session, org: Organization, auth_headers, client: AsyncClient
) -> None:
    first = await seed_master_data(db_session, org.id)
    await db_session.flush()
    second = await seed_master_data(db_session, org.id)
    await db_session.flush()

    count_result = await db_session.execute(
        select(func.count()).select_from(Product).where(Product.organization_id == org.id)
    )
    total = count_result.scalar_one()

    assert first["products"] == 6
    assert second["products"] == 0
    assert total == 6

    response = await client.get("/api/v1/products", headers=auth_headers, params={"page_size": 100})
    assert response.status_code == 200
    assert response.json()["total"] == 6


@pytest.mark.asyncio
async def test_create_product_duplicate_code_fails(
    client: AsyncClient, seeded_org, auth_headers
) -> None:
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "code": "ETANOL_HIDRATADO",
            "name": "Duplicado",
            "fuel_family": "ETHANOL",
            "commercial_variant": "COMMON",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_CODE_ALREADY_EXISTS"


# --- ERP products ---


@pytest.mark.asyncio
async def test_erp_product_unique_per_station(
    client: AsyncClient,
    db_session,
    seeded_org,
    auth_headers,
    branch_station: Station,
    headquarters: Station,
) -> None:
    rows = [{"erp_product_id": "XP-001", "erp_description": "Gasolina ERP"}]
    await _import_erp_products(client, auth_headers, branch_station.id, rows)
    await _import_erp_products(client, auth_headers, headquarters.id, rows)

    branch_count = await db_session.execute(
        select(func.count())
        .select_from(ErpProduct)
        .where(
            ErpProduct.station_id == branch_station.id,
            ErpProduct.erp_product_id == "XP-001",
        )
    )
    hq_count = await db_session.execute(
        select(func.count())
        .select_from(ErpProduct)
        .where(
            ErpProduct.station_id == headquarters.id,
            ErpProduct.erp_product_id == "XP-001",
        )
    )
    assert branch_count.scalar_one() == 1
    assert hq_count.scalar_one() == 1

    reimport = await _upload_erp_products_csv(client, auth_headers, branch_station.id, rows)
    assert reimport.status_code == 201
    job = reimport.json()
    assert job["records_unchanged"] == 1
    assert job["records_inserted"] == 0


@pytest.mark.asyncio
async def test_erp_product_map_ignore_reopen_remap_with_history(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station, admin_user: User
) -> None:
    await _import_erp_products(
        client,
        auth_headers,
        branch_station.id,
        [{"erp_product_id": "XP-MAP-01", "erp_description": "Etanol ERP"}],
    )
    list_resp = await client.get(
        "/api/v1/erp-products",
        headers=auth_headers,
        params={"station_id": str(branch_station.id), "mapping_status": "PENDING"},
    )
    erp_product_id = list_resp.json()["items"][0]["id"]
    product_a = await _get_seeded_product_id(client, auth_headers, "ETANOL_HIDRATADO")
    product_b = await _get_seeded_product_id(client, auth_headers, "GASOLINA_C_COMUM")

    map_resp = await client.post(
        f"/api/v1/erp-products/{erp_product_id}/map",
        headers=auth_headers,
        json={"canonical_product_id": product_a},
    )
    assert map_resp.status_code == 200
    assert map_resp.json()["mapping_status"] == "MAPPED"
    assert map_resp.json()["canonical_product_id"] == product_a

    ignore_resp = await client.post(
        f"/api/v1/erp-products/{erp_product_id}/ignore",
        headers=auth_headers,
        json={"reason": "Produto descontinuado no ERP"},
    )
    assert ignore_resp.status_code == 200
    assert ignore_resp.json()["mapping_status"] == "IGNORED"

    reopen_resp = await client.post(
        f"/api/v1/erp-products/{erp_product_id}/reopen",
        headers=auth_headers,
        json={"reason": "Revisão de mapeamento"},
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["mapping_status"] == "PENDING"

    remap_resp = await client.post(
        f"/api/v1/erp-products/{erp_product_id}/map",
        headers=auth_headers,
        json={"canonical_product_id": product_b, "reason": "Correção de classificação"},
    )
    assert remap_resp.status_code == 200
    assert remap_resp.json()["canonical_product_id"] == product_b

    history_resp = await client.get(
        f"/api/v1/erp-products/{erp_product_id}/history",
        headers=auth_headers,
    )
    assert history_resp.status_code == 200
    history = history_resp.json()["items"]
    assert len(history) >= 4
    statuses = [entry["new_status"] for entry in history]
    assert "MAPPED" in statuses
    assert "IGNORED" in statuses
    assert "PENDING" in statuses


@pytest.mark.asyncio
async def test_erp_product_bulk_map(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station
) -> None:
    await _import_erp_products(
        client,
        auth_headers,
        branch_station.id,
        [
            {"erp_product_id": "XP-BULK-01", "erp_description": "Produto bulk 1"},
            {"erp_product_id": "XP-BULK-02", "erp_description": "Produto bulk 2"},
        ],
    )
    list_resp = await client.get(
        "/api/v1/erp-products",
        headers=auth_headers,
        params={"station_id": str(branch_station.id), "mapping_status": "PENDING", "page_size": 100},
    )
    erp_ids = [item["id"] for item in list_resp.json()["items"] if item["erp_product_id"].startswith("XP-BULK")]
    canonical_id = await _get_seeded_product_id(client, auth_headers, "DIESEL_B_S10_COMUM")

    bulk_resp = await client.post(
        "/api/v1/erp-products/bulk-map",
        headers=auth_headers,
        json={
            "erp_product_ids": erp_ids,
            "canonical_product_id": canonical_id,
            "reason": "Mapeamento em lote",
        },
    )
    assert bulk_resp.status_code == 200
    data = bulk_resp.json()
    assert len(data["mapped"]) == 2
    assert data["failures"] == []
    for item in data["mapped"]:
        assert item["mapping_status"] == "MAPPED"
        assert item["canonical_product_id"] == canonical_id


# --- CSV import ---


@pytest.mark.asyncio
async def test_csv_import_valid_idempotent_preserves_mapping(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station
) -> None:
    rows = [{"erp_product_id": "XP-CSV-01", "erp_description": "Diesel importado", "erp_unit": "L"}]
    upload1, confirm1 = await _import_erp_products(client, auth_headers, branch_station.id, rows)
    assert upload1["status"] == "READY"
    assert confirm1["status"] == "SUCCESS"
    assert confirm1["records_inserted"] == 1

    list_resp = await client.get(
        "/api/v1/erp-products",
        headers=auth_headers,
        params={"station_id": str(branch_station.id), "search": "XP-CSV-01"},
    )
    erp_product_id = list_resp.json()["items"][0]["id"]
    canonical_id = await _get_seeded_product_id(client, auth_headers, "DIESEL_B_S500_COMUM")
    await client.post(
        f"/api/v1/erp-products/{erp_product_id}/map",
        headers=auth_headers,
        json={"canonical_product_id": canonical_id},
    )

    upload2 = await _upload_erp_products_csv(client, auth_headers, branch_station.id, rows)
    assert upload2.status_code == 201
    job2 = upload2.json()
    assert job2["records_unchanged"] == 1
    assert job2["records_inserted"] == 0

    confirm2 = await _confirm_import(client, auth_headers, job2["id"])
    assert confirm2.status_code == 200
    assert confirm2.json()["records_unchanged"] == 1

    after = await client.get(f"/api/v1/erp-products/{erp_product_id}", headers=auth_headers)
    assert after.status_code == 200
    assert after.json()["mapping_status"] == "MAPPED"
    assert after.json()["canonical_product_id"] == canonical_id


# --- Distributors & bases ---


@pytest.mark.asyncio
async def test_distributor_cnpj_duplicate_rejected(client: AsyncClient, seeded_org, auth_headers) -> None:
    first = await _create_distributor(client, auth_headers, internal_code="DIST-A", cnpj="11222333000858")
    assert first.status_code == 201

    second = await _create_distributor(
        client,
        auth_headers,
        internal_code="DIST-B",
        cnpj="11222333000858",
        trade_name="Outra Distribuidora",
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DISTRIBUTOR_CNPJ_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_distribution_base_duplicate_rejected(client: AsyncClient, seeded_org, auth_headers) -> None:
    distributor = await _create_distributor(
        client, auth_headers, internal_code="DIST-BASE", cnpj="11222333000424"
    )
    assert distributor.status_code == 201
    distributor_id = distributor.json()["id"]
    payload = {
        "distributor_id": distributor_id,
        "name": "Base Cuiabá",
        "city": "Cuiabá",
        "state": "MT",
    }

    first = await client.post("/api/v1/distribution-bases", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/distribution-bases", headers=auth_headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DISTRIBUTION_BASE_ALREADY_EXISTS"


# --- Payment terms ---


@pytest.mark.asyncio
async def test_payment_term_cash_requires_zero_days(client: AsyncClient, seeded_org, auth_headers) -> None:
    response = await client.post(
        "/api/v1/payment-terms",
        headers=auth_headers,
        json={
            "code": "CASH_INVALID",
            "name": "À vista inválido",
            "payment_type": "CASH",
            "days": 7,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAYMENT_TERM"


@pytest.mark.asyncio
async def test_payment_term_term_requires_positive_days(
    client: AsyncClient, seeded_org, auth_headers
) -> None:
    response = await client.post(
        "/api/v1/payment-terms",
        headers=auth_headers,
        json={
            "code": "TERM_INVALID",
            "name": "Prazo inválido",
            "payment_type": "TERM",
            "days": 0,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAYMENT_TERM"


@pytest.mark.asyncio
async def test_seeded_payment_terms_cash_and_term_rules(
    client: AsyncClient, seeded_org, auth_headers
) -> None:
    cash = await client.get(
        "/api/v1/payment-terms", headers=auth_headers, params={"payment_type": "CASH"}
    )
    term = await client.get(
        "/api/v1/payment-terms", headers=auth_headers, params={"payment_type": "TERM"}
    )
    assert cash.status_code == 200
    assert term.status_code == 200
    for item in cash.json()["items"]:
        assert item["days"] == 0
    for item in term.json()["items"]:
        assert item["days"] > 0


# --- Supplier rules ---


@pytest.mark.asyncio
async def test_supplier_rule_specific_beats_general(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station
) -> None:
    distributor = await _create_distributor(
        client, auth_headers, internal_code="DIST-RULE", cnpj="11222333000696"
    )
    distributor_id = distributor.json()["id"]
    product_id = await _get_seeded_product_id(client, auth_headers, "GASOLINA_C_COMUM")
    valid_from = date.today().isoformat()

    general = await client.post(
        "/api/v1/station-supplier-rules",
        headers=auth_headers,
        json={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "allowed": True,
            "minimum_volume_liters": "8000.000",
            "valid_from": valid_from,
            "priority": 100,
        },
    )
    assert general.status_code == 201

    specific = await client.post(
        "/api/v1/station-supplier-rules",
        headers=auth_headers,
        json={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "product_id": product_id,
            "allowed": True,
            "minimum_volume_liters": "3000.000",
            "valid_from": valid_from,
            "priority": 100,
        },
    )
    assert specific.status_code == 201

    effective = await client.get(
        "/api/v1/station-supplier-rules/effective",
        headers=auth_headers,
        params={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "product_id": product_id,
        },
    )
    assert effective.status_code == 200
    data = effective.json()
    assert data["rule_source"] == "PRODUCT_SPECIFIC"
    assert data["rule_id"] == specific.json()["id"]
    assert Decimal(str(data["minimum_volume_liters"])) == Decimal("3000.000")


@pytest.mark.asyncio
async def test_supplier_rule_overlap_blocked(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station
) -> None:
    distributor = await _create_distributor(
        client, auth_headers, internal_code="DIST-OVERLAP", cnpj="11222333000777"
    )
    distributor_id = distributor.json()["id"]
    product_id = await _get_seeded_product_id(client, auth_headers, "ETANOL_HIDRATADO")
    valid_from = date.today().isoformat()
    payload = {
        "station_id": str(branch_station.id),
        "distributor_id": distributor_id,
        "product_id": product_id,
        "allowed": True,
        "minimum_volume_liters": "5000.000",
        "valid_from": valid_from,
        "priority": 100,
    }

    first = await client.post("/api/v1/station-supplier-rules", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/station-supplier-rules", headers=auth_headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "SUPPLIER_RULE_OVERLAP"


@pytest.mark.asyncio
async def test_supplier_rule_effective_endpoint_general_fallback(
    client: AsyncClient, seeded_org, auth_headers, branch_station: Station
) -> None:
    distributor = await _create_distributor(
        client, auth_headers, internal_code="DIST-EFFECTIVE", cnpj="11222333000505"
    )
    distributor_id = distributor.json()["id"]
    product_id = await _get_seeded_product_id(client, auth_headers, "DIESEL_B_S10_ADITIVADO")
    valid_from = date.today().isoformat()

    general = await client.post(
        "/api/v1/station-supplier-rules",
        headers=auth_headers,
        json={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "allowed": False,
            "minimum_volume_liters": "6000.000",
            "valid_from": valid_from,
            "priority": 100,
            "reason": "Bloqueio geral",
        },
    )
    assert general.status_code == 201

    effective = await client.get(
        "/api/v1/station-supplier-rules/effective",
        headers=auth_headers,
        params={
            "station_id": str(branch_station.id),
            "distributor_id": distributor_id,
            "product_id": product_id,
        },
    )
    assert effective.status_code == 200
    data = effective.json()
    assert data["rule_source"] == "DISTRIBUTOR_GENERAL"
    assert data["allowed"] is False
    assert data["rule_id"] == general.json()["id"]


# --- Permissions ---


@pytest.mark.asyncio
async def test_financeiro_cannot_map_erp_product(
    client: AsyncClient,
    seeded_org,
    financeiro_headers,
    auth_headers,
    branch_station: Station,
) -> None:
    await _import_erp_products(
        client,
        auth_headers,
        branch_station.id,
        [{"erp_product_id": "XP-PERM-01", "erp_description": "Permissão financeiro"}],
    )
    list_resp = await client.get(
        "/api/v1/erp-products",
        headers=financeiro_headers,
        params={"station_id": str(branch_station.id), "search": "XP-PERM-01"},
    )
    assert list_resp.status_code == 200
    erp_product_id = list_resp.json()["items"][0]["id"]
    product_id = await _get_seeded_product_id(client, auth_headers, "ETANOL_HIDRATADO")

    map_resp = await client.post(
        f"/api/v1/erp-products/{erp_product_id}/map",
        headers=financeiro_headers,
        json={"canonical_product_id": product_id},
    )
    assert map_resp.status_code == 403
    assert map_resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_comprador_can_create_distributor(client: AsyncClient, seeded_org, comprador_headers) -> None:
    response = await _create_distributor(
        client,
        comprador_headers,
        internal_code="DIST-COMP",
        cnpj="11222333000939",
        trade_name="Distribuidora Comprador",
    )
    assert response.status_code == 201
    assert response.json()["trade_name"] == "Distribuidora Comprador"


@pytest.mark.asyncio
async def test_consulta_read_only_master_data(
    client: AsyncClient, seeded_org, consulta_headers, branch_station: Station
) -> None:
    read_products = await client.get("/api/v1/products", headers=consulta_headers)
    read_distributors = await client.get("/api/v1/distributors", headers=consulta_headers)
    read_terms = await client.get("/api/v1/payment-terms", headers=consulta_headers)
    read_erp = await client.get(
        "/api/v1/erp-products",
        headers=consulta_headers,
        params={"station_id": str(branch_station.id)},
    )

    assert read_products.status_code == 200
    assert read_distributors.status_code == 200
    assert read_terms.status_code == 200
    assert read_erp.status_code == 200

    write_product = await client.post(
        "/api/v1/products",
        headers=consulta_headers,
        json={
            "code": "NOVO_PROD",
            "name": "Novo",
            "fuel_family": "ETHANOL",
            "commercial_variant": "COMMON",
        },
    )
    write_distributor = await client.post(
        "/api/v1/distributors",
        headers=consulta_headers,
        json={
            "internal_code": "DIST-CONS",
            "corporate_name": "Consulta LTDA",
            "trade_name": "Consulta",
            "cnpj": "11222333000858",
        },
    )

    assert write_product.status_code == 403
    assert write_distributor.status_code == 403
