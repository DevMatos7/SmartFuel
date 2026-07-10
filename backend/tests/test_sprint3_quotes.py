"""Testes Sprint 3 — central de cotações manual."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.payment_term import PaymentTerm
from app.models.product import Product
from app.models.quote import Quote
from factories import create_user, login, seed_master_data

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_distributor(client: AsyncClient, headers: dict[str, str], *, code: str = "DIST-Q") -> dict:
    response = await client.post(
        "/api/v1/distributors",
        headers=headers,
        json={
            "internal_code": code,
            "corporate_name": f"{code} LTDA",
            "trade_name": f"Distribuidora {code}",
            "cnpj": "11222333000858",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _quote_payload(station_id: str, distributor_id: str, *, channel: str = "WHATSAPP") -> dict:
    now = datetime.now(UTC)
    return {
        "station_id": station_id,
        "distributor_id": distributor_id,
        "quoted_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=5)).isoformat(),
        "source_channel": channel,
        "entry_method": "MANUAL",
        "seller_name": "Vendedor Teste",
        "seller_contact": "65999990000",
        "notes": "Observação de teste",
    }


async def _create_draft_quote(
    client: AsyncClient,
    headers: dict[str, str],
    station_id: str,
    distributor_id: str,
    *,
    channel: str = "WHATSAPP",
) -> dict:
    response = await client.post(
        "/api/v1/quotes",
        headers=headers,
        json=await _quote_payload(station_id, distributor_id, channel=channel),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _add_item(
    client: AsyncClient,
    headers: dict[str, str],
    quote_id: str,
    *,
    version: int,
    product_id: str,
    payment_term_id: str,
    price: str = "5.3200",
) -> dict:
    response = await client.post(
        f"/api/v1/quotes/{quote_id}/items",
        headers=headers,
        json={
            "expected_version": version,
            "product_id": product_id,
            "payment_term_id": payment_term_id,
            "quoted_price_per_liter": price,
            "minimum_volume_liters": "5000.000",
            "freight_type": "CIF",
            "freight_calculation_type": "NONE",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _upload_evidence(client: AsyncClient, headers: dict[str, str], quote_id: str, version: int) -> dict:
    response = await client.post(
        f"/api/v1/quotes/{quote_id}/evidences",
        headers=headers,
        data={"expected_version": str(version), "category": "PDF_PROPOSAL"},
        files={"file": ("proposta.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def comprador_user(db_session, org, branch_station):
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="comprador-s3@test.com",
        role_codes=["COMPRADOR"],
        station_ids=[branch_station.id],
    )
    await db_session.flush()
    return user


@pytest.fixture
async def comprador_headers(client: AsyncClient, comprador_user) -> dict[str, str]:
    token, _ = await login(client, "comprador-s3@test.com", "SenhaSegura123")
    return _auth(token)


@pytest.fixture
async def master_context(db_session, org, auth_headers, client, headquarters):
    await seed_master_data(db_session, org.id)
    await db_session.flush()
    distributor = await _create_distributor(client, auth_headers)
    products = await client.get("/api/v1/products", headers=auth_headers)
    terms = await client.get("/api/v1/payment-terms", headers=auth_headers)
    assert products.status_code == 200
    assert terms.status_code == 200
    return {
        "station_id": str(headquarters.id),
        "distributor_id": distributor["id"],
        "product_id": products.json()["items"][0]["id"],
        "payment_term_id": terms.json()["items"][0]["id"],
    }


async def test_create_draft_quote(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    assert quote["status"] == "DRAFT"
    assert quote["version"] == 1
    assert quote["quote_number"] >= 1


async def test_add_item_and_duplicate_blocked(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    dup = await client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        headers=auth_headers,
        json={
            "expected_version": quote["version"],
            "product_id": master_context["product_id"],
            "payment_term_id": master_context["payment_term_id"],
            "quoted_price_per_liter": "5.3200",
            "minimum_volume_liters": "5000.000",
            "freight_type": "CIF",
            "freight_calculation_type": "NONE",
        },
    )
    assert dup.status_code == 400
    assert dup.json()["error"]["code"] == "DUPLICATE_QUOTE_ITEM"


async def test_activate_requires_evidence_for_whatsapp(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
        channel="WHATSAPP",
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    response = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=auth_headers,
        json={"expected_version": quote["version"]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QUOTE_EVIDENCE_REQUIRED"


async def test_activate_quote_flow(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    response = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=auth_headers,
        json={"expected_version": quote["version"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["effective_status"] == "ACTIVE"


async def test_active_quote_not_editable(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    activated = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=auth_headers,
        json={"expected_version": quote["version"]},
    )
    quote = activated.json()
    patch = await client.patch(
        f"/api/v1/quotes/{quote['id']}",
        headers=auth_headers,
        json={"expected_version": quote["version"], "notes": "tentativa"},
    )
    assert patch.status_code == 400
    assert patch.json()["error"]["code"] == "QUOTE_NOT_EDITABLE"


async def test_version_conflict(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    first = await client.patch(
        f"/api/v1/quotes/{quote['id']}",
        headers=auth_headers,
        json={"expected_version": 1, "notes": "primeira"},
    )
    assert first.status_code == 200
    conflict = await client.patch(
        f"/api/v1/quotes/{quote['id']}",
        headers=auth_headers,
        json={"expected_version": 1, "notes": "conflito"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "QUOTE_VERSION_CONFLICT"


async def test_revise_active_quote(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    activated = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=auth_headers,
        json={"expected_version": quote["version"]},
    )
    assert activated.status_code == 200, activated.text
    active = activated.json()
    revision = await client.post(
        f"/api/v1/quotes/{active['id']}/revise",
        headers=auth_headers,
        json={"reason": "Preço corrigido"},
    )
    assert revision.status_code == 201, revision.text
    draft = revision.json()
    assert draft["status"] == "DRAFT"
    assert draft["replaces_quote_id"] == active["id"]
    assert len(draft["items"]) == 1


async def test_cancel_requires_reason(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    response = await client.post(
        f"/api/v1/quotes/{quote['id']}/cancel",
        headers=auth_headers,
        json={"expected_version": quote["version"], "reason": "  "},
    )
    assert response.status_code == 400


async def test_expiration_job(client, auth_headers, master_context, db_session) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    assert "id" in quote, quote
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    activated = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=auth_headers,
        json={"expected_version": quote["version"]},
    )
    assert activated.status_code == 200, activated.text
    active = activated.json()
    db_quote = await db_session.get(Quote, uuid.UUID(active["id"]))
    db_quote.quoted_at = datetime.now(UTC) - timedelta(hours=2)
    db_quote.valid_until = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.flush()

    run = await client.post("/api/v1/quotes/expiration/run", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["expired_count"] >= 1

    refreshed = await client.get(f"/api/v1/quotes/{active['id']}", headers=auth_headers)
    assert refreshed.json()["status"] == "EXPIRED"


async def test_consulta_cannot_create_quote(client, consulta_user, branch_station, master_context) -> None:
    token, _ = await login(client, "consulta@test.com", "SenhaSegura123")
    headers = _auth(token)
    response = await client.post(
        "/api/v1/quotes",
        headers=headers,
        json=await _quote_payload(master_context["station_id"], master_context["distributor_id"]),
    )
    assert response.status_code == 403


async def test_quote_history_recorded(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client,
        auth_headers,
        master_context["station_id"],
        master_context["distributor_id"],
    )
    history = await client.get(f"/api/v1/quotes/{quote['id']}/history", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["total"] >= 1
    assert any(item["action"] == "CREATED" for item in history.json()["items"])
