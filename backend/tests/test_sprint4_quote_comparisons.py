"""Testes Sprint 4 — comparação de cotações e parâmetros financeiros."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.domain.quote_comparison.formulas import (
    compute_daily_rate,
    compute_delivered_cost_per_liter,
    compute_financial_equivalent_cost_per_liter,
    compute_freight_per_liter,
)
from app.domain.quote_comparison.ranking import RankableOffer, sort_offers
from factories import create_user, login, seed_master_data

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_distributor(client: AsyncClient, headers: dict[str, str], *, code: str) -> dict:
    cnpj_by_code = {
        "DIST-A": "11222333000858",
        "DIST-B": "11222333000424",
        "DIST-C": "11222333000696",
    }
    response = await client.post(
        "/api/v1/distributors",
        headers=headers,
        json={
            "internal_code": code,
            "corporate_name": f"{code} LTDA",
            "trade_name": f"Distribuidora {code}",
            "cnpj": cnpj_by_code.get(code, "11222333000777"),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_active_quote(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    station_id: str,
    distributor_id: str,
    product_id: str,
    payment_term_id: str,
    price: str,
    minimum_volume: str = "5000.000",
    freight_calculation_type: str = "NONE",
    freight_value_total: str | None = None,
    payment_term_days: int | None = None,
    channel: str = "EMAIL",
) -> dict:
    now = datetime.now(UTC)
    response = await client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "station_id": station_id,
            "distributor_id": distributor_id,
            "quoted_at": now.isoformat(),
            "valid_until": (now + timedelta(days=2)).isoformat(),
            "source_channel": channel,
            "entry_method": "MANUAL",
            "seller_name": "Vendedor Teste",
            "seller_contact": "65999990000",
        },
    )
    assert response.status_code == 201, response.text
    quote = response.json()
    item_payload: dict = {
        "expected_version": quote["version"],
        "product_id": product_id,
        "payment_term_id": payment_term_id,
        "quoted_price_per_liter": price,
        "minimum_volume_liters": minimum_volume,
        "freight_type": "FOB" if freight_calculation_type != "NONE" else "CIF",
        "freight_calculation_type": freight_calculation_type,
    }
    if freight_value_total is not None:
        item_payload["freight_value_total"] = freight_value_total
    item_response = await client.post(
        f"/api/v1/quotes/{quote['id']}/items",
        headers=headers,
        json=item_payload,
    )
    assert item_response.status_code == 201, item_response.text
    refreshed = await client.get(f"/api/v1/quotes/{quote['id']}", headers=headers)
    assert refreshed.status_code == 200, refreshed.text
    quote = refreshed.json()
    evidence = await client.post(
        f"/api/v1/quotes/{quote['id']}/evidences",
        headers=headers,
        data={"expected_version": str(quote["version"]), "category": "PDF_PROPOSAL"},
        files={"file": ("proposta.pdf", PDF_BYTES, "application/pdf")},
    )
    assert evidence.status_code == 200, evidence.text
    quote = evidence.json()
    activated = await client.post(
        f"/api/v1/quotes/{quote['id']}/activate",
        headers=headers,
        json={"expected_version": quote["version"]},
    )
    assert activated.status_code == 200, activated.text
    return activated.json()


@pytest.fixture
async def master_context(db_session, org, auth_headers, client, headquarters):
    await seed_master_data(db_session, org.id)
    await db_session.flush()
    dist_a = await _create_distributor(client, auth_headers, code="DIST-A")
    dist_b = await _create_distributor(client, auth_headers, code="DIST-B")
    products = await client.get("/api/v1/products", headers=auth_headers)
    terms = await client.get("/api/v1/payment-terms", headers=auth_headers)
    assert products.status_code == 200
    assert terms.status_code == 200
    product_id = products.json()["items"][0]["id"]
    valid_from = datetime.now(UTC).date().isoformat()
    for distributor_id in (dist_a["id"], dist_b["id"]):
        rule = await client.post(
            "/api/v1/station-supplier-rules",
            headers=auth_headers,
            json={
                "station_id": str(headquarters.id),
                "distributor_id": distributor_id,
                "product_id": product_id,
                "allowed": True,
                "minimum_volume_liters": "5000.000",
                "valid_from": valid_from,
                "priority": 100,
                "reason": "Regra de teste Sprint 4",
            },
        )
        assert rule.status_code == 201, rule.text
    cash_term = next(t for t in terms.json()["items"] if t["days"] == 0)
    term_21 = next((t for t in terms.json()["items"] if t["days"] == 21), terms.json()["items"][0])
    return {
        "station_id": str(headquarters.id),
        "product_id": product_id,
        "cash_term_id": cash_term["id"],
        "term_21_id": term_21["id"],
        "dist_a": dist_a["id"],
        "dist_b": dist_b["id"],
    }


def test_daily_rate_uses_effective_conversion() -> None:
    rate = compute_daily_rate(annual_effective_rate=Decimal("0.15"), day_count_basis=365)
    simple = Decimal("0.15") / Decimal("365")
    assert rate != simple
    assert rate > Decimal("0")


def test_freight_total_divides_by_requested_volume() -> None:
    freight = compute_freight_per_liter(
        freight_calculation_type="TOTAL",
        freight_value_per_liter=None,
        freight_value_total=Decimal("3000"),
        requested_volume_liters=Decimal("30000"),
    )
    assert freight == Decimal("0.10000000")


def test_delivered_cost_formula() -> None:
    delivered = compute_delivered_cost_per_liter(
        quoted_price_per_liter=Decimal("5.20"),
        discount_per_liter=Decimal("0.02"),
        rebate_per_liter=Decimal("0.01"),
        freight_per_liter=Decimal("0.10"),
        other_cost_per_liter=Decimal("0.005"),
    )
    assert delivered == Decimal("5.27500000")


def test_financial_equivalent_cash_equals_delivered() -> None:
    delivered = Decimal("5.30")
    equivalent = compute_financial_equivalent_cost_per_liter(
        delivered_cost_per_liter=delivered,
        daily_rate=Decimal("0.00038212"),
        financial_days=0,
    )
    assert equivalent == delivered


def test_ranking_tie_break_is_deterministic() -> None:
    base_time = datetime.now(UTC)
    offers = [
        RankableOffer(
            item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            distributor_name="Beta",
            ranking_cost=Decimal("5.30"),
            financial_equivalent_cost=Decimal("5.30"),
            delivered_cost=Decimal("5.30"),
            raw_price=Decimal("5.20"),
            delivery_expected_at=base_time + timedelta(hours=8),
            effective_valid_until=base_time + timedelta(days=1),
            activated_at=base_time,
            eligibility_status="ELIGIBLE",
        ),
        RankableOffer(
            item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            distributor_name="Alpha",
            ranking_cost=Decimal("5.30"),
            financial_equivalent_cost=Decimal("5.30"),
            delivered_cost=Decimal("5.30"),
            raw_price=Decimal("5.20"),
            delivery_expected_at=base_time + timedelta(hours=6),
            effective_valid_until=base_time + timedelta(days=1),
            activated_at=base_time,
            eligibility_status="ELIGIBLE",
        ),
    ]
    ordered = sort_offers(offers)
    assert ordered[0].distributor_name == "Alpha"


async def test_create_financial_parameter(client, auth_headers) -> None:
    now = datetime.now(UTC)
    response = await client.post(
        "/api/v1/financial-parameters",
        headers=auth_headers,
        json={
            "annual_effective_rate": "0.15000000",
            "day_count_basis": 365,
            "valid_from": now.isoformat(),
            "notes": "Taxa de teste",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["annual_effective_rate"] == "0.15000000"
    assert body["active"] is True


async def test_comparison_ranks_by_delivered_cost(client, auth_headers, master_context) -> None:
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/financial-parameters",
        headers=auth_headers,
        json={
            "annual_effective_rate": "0.15000000",
            "day_count_basis": 365,
            "valid_from": (now - timedelta(days=1)).isoformat(),
        },
    )
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.2000",
        freight_calculation_type="TOTAL",
        freight_value_total="3000.00",
    )
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_b"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.2700",
    )
    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "30000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "DELIVERED",
            "ranking_scope": "BEST_PER_DISTRIBUTOR",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "COMPLETED"
    ranked = [r for r in body["results"] if r["rank_position"] is not None]
    assert len(ranked) >= 2
    assert ranked[0]["costs"]["delivered_cost_per_liter"] <= ranked[1]["costs"]["delivered_cost_per_liter"]


async def test_minimum_volume_makes_offer_ineligible(client, auth_headers, master_context) -> None:
    now = datetime.now(UTC)
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.1000",
        minimum_volume="10000.000",
    )
    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "3000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "RAW",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    ineligible = [r for r in body["results"] if r["eligibility_status"] == "INELIGIBLE"]
    assert ineligible
    codes = {reason["code"] for r in ineligible for reason in r["eligibility_reasons"]}
    assert "MINIMUM_VOLUME_NOT_REACHED" in codes


async def test_comparison_datetime_in_future_rejected(client, auth_headers, master_context) -> None:
    future = datetime.now(UTC) + timedelta(days=1)
    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "30000.000",
            "comparison_datetime": future.isoformat(),
            "ranking_mode": "RAW",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "COMPARISON_DATETIME_IN_FUTURE"


async def test_export_comparison_pdf_and_csv(client, auth_headers, master_context) -> None:
    now = datetime.now(UTC)
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.2200",
    )
    created = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "30000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "RAW",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    pdf = await client.get(f"/api/v1/quote-comparisons/{run_id}/export/pdf", headers=auth_headers)
    csv = await client.get(f"/api/v1/quote-comparisons/{run_id}/export/csv", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert csv.status_code == 200
    assert b"eligibility_status" in csv.content
