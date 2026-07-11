"""Testes sintéticos Sprint 11 — fórmulas, guardrails, workflow, no-hindsight."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.pricing_enums import (
    DecisionStatus,
    RecommendationStatus,
)
from app.domain.pricing.formulas import (
    apply_guardrails,
    apply_rounding,
    commercial_floor_price,
    gross_margin_per_liter,
    gross_margin_percentage,
    markup_percentage,
    target_price,
)
from app.models.product import Product
from app.services.pricing_recommendation_service import PricingRecommendationService
from factories import create_organization, create_station, create_user, seed_master_data


def test_margin_per_liter():
    assert gross_margin_per_liter(Decimal("5.50"), Decimal("5.00")) == Decimal("0.50")


def test_margin_percentage():
    pct = gross_margin_percentage(Decimal("5.50"), Decimal("5.00"))
    assert pct is not None
    assert abs(pct - Decimal("0.09090909")) < Decimal("0.0001")


def test_markup_percentage():
    mk = markup_percentage(Decimal("5.50"), Decimal("5.00"))
    assert mk == Decimal("0.1")


def test_missing_cost_never_zero():
    assert gross_margin_per_liter(Decimal("5.50"), None) is None
    assert markup_percentage(Decimal("5.50"), None) is None


def test_floor_by_absolute_and_percentage():
    floor = commercial_floor_price(
        Decimal("5.00"),
        minimum_margin_per_liter=Decimal("0.30"),
        minimum_margin_percentage=Decimal("0.10"),
        minimum_markup_percentage=Decimal("0.08"),
    )
    # max(5.30, 5/0.9≈5.555..., 5.40) = ~5.555
    assert floor is not None
    assert floor > Decimal("5.50")


def test_target_never_below_floor():
    floor = commercial_floor_price(Decimal("5.00"), minimum_margin_per_liter=Decimal("0.40"))
    tgt = target_price(
        Decimal("5.00"),
        target_margin_per_liter=Decimal("0.10"),
        floor=floor,
    )
    assert floor is not None and tgt is not None
    assert tgt >= floor


def test_guardrail_holds_small_change():
    g = apply_guardrails(
        Decimal("5.50"),
        Decimal("5.51"),
        minimum_change_per_liter=Decimal("0.05"),
    )
    assert g.guardrail_applied
    assert g.status_hint == RecommendationStatus.HOLD
    assert g.guarded_recommended_price == Decimal("5.50")


def test_guardrail_caps_increase():
    g = apply_guardrails(
        Decimal("5.00"),
        Decimal("5.50"),
        maximum_increase_per_liter=Decimal("0.10"),
    )
    assert g.guardrail_applied
    assert g.raw_recommended_price == Decimal("5.50")
    assert g.guarded_recommended_price == Decimal("5.10")
    assert g.status_hint == RecommendationStatus.REVIEW_REQUIRED


def test_rounding_respects_floor():
    before, after = apply_rounding(
        Decimal("5.301"),
        "NEAREST_CENT",
        floor=Decimal("5.305"),
    )
    assert before == Decimal("5.301")
    assert after >= Decimal("5.305")


def test_compute_below_floor_increase():
    svc = PricingRecommendationService.__new__(PricingRecommendationService)
    policy = {
        "minimum_margin_per_liter": "0.30",
        "target_margin_per_liter": "0.50",
        "rounding_policy": "NEAREST_CENT",
        "default_scenario": "BALANCED",
        "maximum_increase_per_liter": "1.00",
        "minimum_change_per_liter": "0.01",
    }
    result = svc.compute_recommendation_item(
        policy=policy,
        cost_info={
            "cost_basis_type": "SYNTHETIC_COST",
            "cost_per_liter": Decimal("5.00"),
            "cost_confidence": "HIGH",
            "warnings": [],
        },
        price_info={"current_price": Decimal("5.10"), "warnings": []},
    )
    assert result["recommendation_status"] == RecommendationStatus.INCREASE
    assert "BELOW_COMMERCIAL_FLOOR" in result["reasons"]
    assert result["recommended_price"] is not None
    assert result["recommended_price"] > Decimal("5.10")


def test_compute_missing_cost_no_recommendation():
    svc = PricingRecommendationService.__new__(PricingRecommendationService)
    result = svc.compute_recommendation_item(
        policy={"rounding_policy": "NONE", "default_scenario": "BALANCED"},
        cost_info={
            "cost_basis_type": "SYNTHETIC_COST",
            "cost_per_liter": None,
            "cost_confidence": "UNAVAILABLE",
            "warnings": ["MISSING_COST"],
        },
        price_info={"current_price": Decimal("5.50"), "warnings": []},
    )
    assert result["recommendation_status"] == RecommendationStatus.NO_RECOMMENDATION
    assert result["recommended_price"] is None
    assert result["cost_per_liter"] is None


@pytest.mark.asyncio
async def test_synthetic_run_and_reprocess(db_session):
    org = await create_organization(db_session, cnpj="22333444000191")
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Posto Pricing",
        cnpj="22333444000192",
    )
    await seed_master_data(db_session, org.id)
    product = (
        await db_session.execute(select(Product).where(Product.organization_id == org.id).limit(1))
    ).scalar_one()

    svc = PricingRecommendationService(db_session)
    run = await svc.run_recommendations(
        organization_id=org.id,
        user_id=None,
        data={
            "trigger_type": "SYNTHETIC",
            "station_id": station.id,
            "canonical_product_id": product.id,
            "synthetic_policy": {
                "name": "test",
                "cost_basis_type": "SYNTHETIC_COST",
                "minimum_margin_per_liter": "0.30",
                "target_margin_per_liter": "0.50",
                "rounding_policy": "NEAREST_CENT",
                "default_scenario": "BALANCED",
                "maximum_increase_per_liter": "0.50",
                "minimum_change_per_liter": "0.01",
            },
            "items": [
                {
                    "station_id": station.id,
                    "canonical_product_id": product.id,
                    "synthetic_cost": {"cost_per_liter": "5.00", "cost_confidence": "HIGH"},
                    "synthetic_price": {"current_price": "5.10"},
                }
            ],
        },
    )
    assert run.status == "COMPLETED"
    assert run.item_count == 1
    assert run.snapshot_hash
    original_id = run.id

    re = await svc.reprocess_run(
        run_id=run.id,
        organization_id=org.id,
        user_id=None,
        reason="Homologação reprocessamento",
    )
    assert re.id != original_id
    assert re.reprocess_of_run_id == original_id
    # original preserved
    still = await svc.get_run(original_id, org.id)
    assert still.snapshot_hash == run.snapshot_hash


@pytest.mark.asyncio
async def test_hindsight_blocks_future_cost(db_session):
    org = await create_organization(db_session, cnpj="33444555000193")
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Posto Hindsight",
        cnpj="33444555000194",
    )
    await seed_master_data(db_session, org.id)
    product = (
        await db_session.execute(select(Product).where(Product.organization_id == org.id).limit(1))
    ).scalar_one()
    ref = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    svc = PricingRecommendationService(db_session)
    run = await svc.run_recommendations(
        organization_id=org.id,
        user_id=None,
        data={
            "reference_datetime": ref.isoformat(),
            "synthetic_policy": {
                "name": "hist",
                "cost_basis_type": "SYNTHETIC_COST",
                "minimum_margin_per_liter": "0.30",
                "target_margin_per_liter": "0.50",
                "rounding_policy": "NONE",
                "default_scenario": "BALANCED",
            },
            "items": [
                {
                    "station_id": station.id,
                    "canonical_product_id": product.id,
                    "synthetic_cost": {
                        "cost_per_liter": "5.00",
                        "cost_available_at": (ref + timedelta(days=2)).isoformat(),
                    },
                    "synthetic_price": {"current_price": "5.50"},
                }
            ],
        },
    )
    items = await svc.list_items(org.id)
    item = next(i for i in items if i.recommendation_run_id == run.id)
    assert item.recommendation_status == RecommendationStatus.NO_RECOMMENDATION
    assert item.cost_per_liter is None
    assert any("HINDSIGHT" in str(w) or w == "MISSING_COST" for w in (item.warnings or []))


@pytest.mark.asyncio
async def test_approval_workflow_and_implementation(db_session):
    org = await create_organization(db_session, cnpj="44555666000195")
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Posto WF",
        cnpj="44555666000196",
    )
    creator = await create_user(
        db_session,
        organization_id=org.id,
        email=f"creator-{uuid4().hex[:8]}@test.com",
        role_codes=["GESTOR"],
        has_all_stations_access=True,
    )
    approver = await create_user(
        db_session,
        organization_id=org.id,
        email=f"approver-{uuid4().hex[:8]}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    await seed_master_data(db_session, org.id)
    product = (
        await db_session.execute(select(Product).where(Product.organization_id == org.id).limit(1))
    ).scalar_one()

    svc = PricingRecommendationService(db_session)
    run = await svc.run_recommendations(
        organization_id=org.id,
        user_id=creator.id,
        data={
            "synthetic_policy": {
                "name": "wf",
                "cost_basis_type": "SYNTHETIC_COST",
                "minimum_margin_per_liter": "0.30",
                "target_margin_per_liter": "0.50",
                "rounding_policy": "NEAREST_CENT",
                "default_scenario": "BALANCED",
                "maximum_increase_per_liter": "1.00",
                "minimum_change_per_liter": "0.01",
            },
            "items": [
                {
                    "station_id": station.id,
                    "canonical_product_id": product.id,
                    "synthetic_cost": {"cost_per_liter": "5.00"},
                    "synthetic_price": {"current_price": "5.10"},
                }
            ],
        },
    )
    items = await svc.list_items(org.id)
    item = next(i for i in items if i.recommendation_run_id == run.id)
    assert item.recommended_price is not None

    decision = await svc.create_decision(
        organization_id=org.id,
        user_id=creator.id,
        item_id=item.id,
        data={"required_approvals": 1},
    )
    await svc.submit_decision(decision.id, org.id)

    with pytest.raises(Exception):
        await svc.approve_decision(
            decision_id=decision.id,
            organization_id=org.id,
            user_id=creator.id,
            allow_self_approval=False,
        )

    decision = await svc.approve_decision(
        decision_id=decision.id,
        organization_id=org.id,
        user_id=approver.id,
        allow_self_approval=False,
    )
    assert decision.status == DecisionStatus.APPROVED_PENDING_IMPLEMENTATION
    assert decision.approved_price == item.recommended_price

    await svc.add_evidence(
        decision_id=decision.id,
        organization_id=org.id,
        user_id=approver.id,
        data={"evidence_type": "NOTE", "description": "Print da bomba"},
    )

    check = await svc.confirm_implementation(
        decision_id=decision.id,
        organization_id=org.id,
        user_id=approver.id,
        implemented_price=decision.approved_price + Decimal("0.05"),
        tolerance=Decimal("0.01"),
    )
    assert check.status == "DIFFERENT"
    decision = await svc.get_decision(decision.id, org.id)
    assert decision.status == DecisionStatus.IMPLEMENTED_DIFFERENT


@pytest.mark.asyncio
async def test_dual_approval(db_session):
    org = await create_organization(db_session, cnpj="55666777000197")
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Posto Dual",
        cnpj="55666777000198",
    )
    u1 = await create_user(
        db_session,
        organization_id=org.id,
        email=f"u1-{uuid4().hex[:8]}@test.com",
        role_codes=["GESTOR"],
        has_all_stations_access=True,
    )
    u2 = await create_user(
        db_session,
        organization_id=org.id,
        email=f"u2-{uuid4().hex[:8]}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    await seed_master_data(db_session, org.id)
    product = (
        await db_session.execute(select(Product).where(Product.organization_id == org.id).limit(1))
    ).scalar_one()
    svc = PricingRecommendationService(db_session)
    run = await svc.run_recommendations(
        organization_id=org.id,
        user_id=u1.id,
        data={
            "synthetic_policy": {
                "name": "dual",
                "cost_basis_type": "SYNTHETIC_COST",
                "target_margin_per_liter": "0.50",
                "minimum_margin_per_liter": "0.30",
                "rounding_policy": "NONE",
                "default_scenario": "BALANCED",
            },
            "items": [
                {
                    "station_id": station.id,
                    "canonical_product_id": product.id,
                    "synthetic_cost": {"cost_per_liter": "5.00"},
                    "synthetic_price": {"current_price": "5.20"},
                }
            ],
        },
    )
    item = next(i for i in await svc.list_items(org.id) if i.recommendation_run_id == run.id)
    d = await svc.create_decision(
        organization_id=org.id,
        user_id=u1.id,
        item_id=item.id,
        data={"required_approvals": 2},
    )
    await svc.submit_decision(d.id, org.id)
    d = await svc.approve_decision(decision_id=d.id, organization_id=org.id, user_id=u2.id)
    assert d.status == DecisionStatus.PENDING_APPROVAL
    # second level needs different user - creator can't self-approve; use a third
    u3 = await create_user(
        db_session,
        organization_id=org.id,
        email=f"u3-{uuid4().hex[:8]}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    d = await svc.approve_decision(decision_id=d.id, organization_id=org.id, user_id=u3.id)
    assert d.status == DecisionStatus.APPROVED_PENDING_IMPLEMENTATION


@pytest.mark.asyncio
async def test_no_xpert_write_flag_in_summary(db_session):
    org = await create_organization(db_session, cnpj="66777888000199")
    svc = PricingRecommendationService(db_session)
    summary = await svc.summary(org.id)
    assert summary["xpert_write_enabled"] is False
    assert "lucro líquido" in summary["disclaimer"].lower() or "Margem bruta" in summary["disclaimer"]
