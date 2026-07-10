"""Testes de integração Sprint 4.1 — estabilização do motor de comparação."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.distributor import Distributor
from factories import seed_master_data
from test_sprint4_quote_comparisons import _create_active_quote, _create_distributor


@pytest.fixture
async def master_context(db_session, org, auth_headers, client, headquarters):
    await seed_master_data(db_session, org.id)
    await db_session.flush()
    dist_a = await _create_distributor(client, auth_headers, code="DIST-A")
    dist_b = await _create_distributor(client, auth_headers, code="DIST-B")
    products = await client.get("/api/v1/products", headers=auth_headers)
    terms = await client.get("/api/v1/payment-terms", headers=auth_headers)
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
                "reason": "Regra de teste Sprint 4.1",
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


async def test_deactivated_rule_still_applies_in_historical_resolution(
    client, auth_headers, master_context
) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.1500",
    )
    rules = await client.get("/api/v1/station-supplier-rules", headers=auth_headers)
    rule_id = rules.json()["items"][0]["id"]
    deactivated = await client.post(
        f"/api/v1/station-supplier-rules/{rule_id}/deactivate",
        headers=auth_headers,
        json={"reason": "Teste histórico"},
    )
    assert deactivated.status_code == 200, deactivated.text

    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "30000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "DELIVERED",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["summary"]["eligible_count"] + body["summary"]["warning_count"] >= 1


async def test_export_preserves_snapshot_after_distributor_rename(
    client, auth_headers, master_context, db_session
) -> None:
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
    original_name = created.json()["results"][0]["distributor"]["name"]

    distributor = await db_session.get(Distributor, uuid.UUID(master_context["dist_a"]))
    distributor.trade_name = "Nome Alterado Depois"
    await db_session.flush()

    csv_before = await client.get(
        f"/api/v1/quote-comparisons/{run_id}/export/csv", headers=auth_headers
    )
    assert csv_before.status_code == 200
    assert original_name.encode() in csv_before.content

    detail = await client.get(f"/api/v1/quote-comparisons/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["results"][0]["distributor"]["name"] == original_name


async def test_reprocess_creates_new_run_and_preserves_original(client, auth_headers, master_context) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.1800",
    )
    original = await client.post(
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
    assert original.status_code == 201, original.text
    original_id = original.json()["id"]
    original_hash = original.json()["calculation_hash"]

    reprocessed = await client.post(
        f"/api/v1/quote-comparisons/{original_id}/reprocess",
        headers=auth_headers,
        json={"ranking_mode": "DELIVERED"},
    )
    assert reprocessed.status_code == 201, reprocessed.text
    body = reprocessed.json()
    assert body["id"] != original_id
    assert body["reprocessed_from_run_id"] == original_id
    assert body["scenario"]["ranking_mode"] == "DELIVERED"

    still_original = await client.get(f"/api/v1/quote-comparisons/{original_id}", headers=auth_headers)
    assert still_original.status_code == 200
    assert still_original.json()["calculation_hash"] == original_hash
    assert still_original.json()["scenario"]["ranking_mode"] == "RAW"


async def test_financial_equivalent_without_parameter_marks_ineligible(
    client, auth_headers, master_context
) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["term_21_id"],
        price="5.2400",
    )
    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "30000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "FINANCIAL_EQUIVALENT",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 201, response.text
    codes = {
        reason["code"]
        for result in response.json()["results"]
        for reason in result["eligibility_reasons"]
    }
    assert "MISSING_FINANCIAL_PARAMETER" in codes


async def test_delivered_mode_works_without_financial_parameter(client, auth_headers, master_context) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.2100",
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
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 201, response.text
    ranked = [r for r in response.json()["results"] if r["rank_position"] is not None]
    assert ranked


async def test_minimum_volume_equal_is_eligible(client, auth_headers, master_context) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.2000",
        minimum_volume="5000.000",
    )
    response = await client.post(
        "/api/v1/quote-comparisons",
        headers=auth_headers,
        json={
            "station_id": master_context["station_id"],
            "product_id": master_context["product_id"],
            "requested_volume_liters": "5000.000",
            "comparison_datetime": datetime.now(UTC).isoformat(),
            "ranking_mode": "RAW",
            "ranking_scope": "ALL_OFFERS",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["results"][0]["eligibility_status"] in {"ELIGIBLE", "ELIGIBLE_WITH_WARNINGS"}


async def test_comparison_hash_is_present_and_stable_on_reread(client, auth_headers, master_context) -> None:
    await _create_active_quote(
        client,
        auth_headers,
        station_id=master_context["station_id"],
        distributor_id=master_context["dist_a"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["cash_term_id"],
        price="5.1900",
    )
    created = await client.post(
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
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    first_hash = created.json()["calculation_hash"]
    assert first_hash

    reread = await client.get(f"/api/v1/quote-comparisons/{run_id}", headers=auth_headers)
    assert reread.json()["calculation_hash"] == first_hash
