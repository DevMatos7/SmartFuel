"""Sprint 8.1 — E2E no-hindsight: compra × cotações históricas via orquestrador."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.purchase_benchmark_enums import (
    BenchmarkDecisionResult,
    BenchmarkItemStatus,
    BenchmarkOverrideType,
)
from app.core.quote_comparison_enums import EligibilityStatus
from app.models.distributor import Distributor
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.payment_term import PaymentTerm
from app.models.product import Product
from app.models.purchase_benchmarks import (
    PurchaseBenchmarkOverride,
    PurchaseQuoteBenchmarkCandidate,
    PurchaseQuoteBenchmarkItem,
    PurchaseQuoteBenchmarkRun,
)
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.station_supplier_rule import StationSupplierRule
from app.services.purchase_quote_benchmark_service import PurchaseQuoteBenchmarkService
from factories import create_user, seed_master_data

T = datetime(2026, 7, 9, 10, 0, tzinfo=UTC)


async def _dist(db, org_id: uuid.UUID, code: str, cnpj: str) -> Distributor:
    d = Distributor(
        organization_id=org_id,
        internal_code=code,
        corporate_name=f"{code} LTDA",
        trade_name=code,
        normalized_name=code.upper(),
        cnpj=cnpj,
        active=True,
    )
    db.add(d)
    await db.flush()
    return d


async def _quote_with_item(
    *,
    db,
    org_id: uuid.UUID,
    station_id: uuid.UUID,
    distributor_id: uuid.UUID,
    product_id: uuid.UUID,
    payment_term: PaymentTerm,
    user_id: uuid.UUID,
    quote_number: int,
    activated_at: datetime,
    valid_until: datetime,
    price: Decimal,
    minimum_volume: Decimal,
) -> tuple[Quote, QuoteItem]:
    q = Quote(
        organization_id=org_id,
        station_id=station_id,
        distributor_id=distributor_id,
        quote_number=quote_number,
        quoted_at=activated_at,
        valid_until=valid_until,
        source_channel="EMAIL",
        entry_method="MANUAL",
        status="ACTIVE",
        version=1,
        activated_at=activated_at,
        activated_by=user_id,
        created_by=user_id,
    )
    db.add(q)
    await db.flush()
    item = QuoteItem(
        quote_id=q.id,
        product_id=product_id,
        sequence=1,
        quoted_price_per_liter=price,
        payment_term_id=payment_term.id,
        payment_type_snapshot=payment_term.payment_type,
        payment_term_days_snapshot=payment_term.days,
        payment_term_name_snapshot=payment_term.name,
        freight_type="CIF",
        freight_calculation_type="NONE",
        discount_per_liter=Decimal("0"),
        rebate_per_liter=Decimal("0"),
        other_cost_per_liter=Decimal("0"),
        minimum_volume_liters=minimum_volume,
    )
    db.add(item)
    await db.flush()
    return q, item


@pytest.mark.asyncio
async def test_purchase_benchmark_no_hindsight_e2e(db_session, org, headquarters):
    await seed_master_data(db_session, org.id)
    user = await create_user(
        db_session,
        organization_id=org.id,
        email=f"bench-{uuid.uuid4().hex[:8]}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    product = (
        await db_session.execute(select(Product).where(Product.organization_id == org.id).limit(1))
    ).scalar_one()
    term = (
        await db_session.execute(
            select(PaymentTerm).where(PaymentTerm.organization_id == org.id).limit(1)
        )
    ).scalar_one()

    dist_a = await _dist(db_session, org.id, "BH-A", "11222333000858")
    dist_b = await _dist(db_session, org.id, "BH-B", "11222333000424")
    dist_c = await _dist(db_session, org.id, "BH-C", "11222333000696")
    dist_d = await _dist(db_session, org.id, "BH-D", "11222333000777")

    for dist in (dist_a, dist_b, dist_c, dist_d):
        db_session.add(
            StationSupplierRule(
                organization_id=org.id,
                station_id=headquarters.id,
                distributor_id=dist.id,
                product_id=product.id,
                allowed=True,
                minimum_volume_liters=Decimal("1000"),
                valid_from=date(2026, 1, 1),
                priority=100,
                active=True,
                created_by=user.id,
                reason="E2E Sprint 8.1",
            )
        )
    await db_session.flush()

    # A: antes de T, elegível, preço alto
    qa, ia = await _quote_with_item(
        db=db_session,
        org_id=org.id,
        station_id=headquarters.id,
        distributor_id=dist_a.id,
        product_id=product.id,
        payment_term=term,
        user_id=user.id,
        quote_number=81001,
        activated_at=T - timedelta(days=2),
        valid_until=T + timedelta(days=5),
        price=Decimal("6.50"),
        minimum_volume=Decimal("1000"),
    )
    # B: DEPOIS de T — não pode aparecer
    qb, ib = await _quote_with_item(
        db=db_session,
        org_id=org.id,
        station_id=headquarters.id,
        distributor_id=dist_b.id,
        product_id=product.id,
        payment_term=term,
        user_id=user.id,
        quote_number=81002,
        activated_at=T + timedelta(hours=2),
        valid_until=T + timedelta(days=5),
        price=Decimal("5.00"),
        minimum_volume=Decimal("1000"),
    )
    # C: antes de T, inelegível por volume mínimo 20000 (compra 4000)
    qc, ic = await _quote_with_item(
        db=db_session,
        org_id=org.id,
        station_id=headquarters.id,
        distributor_id=dist_c.id,
        product_id=product.id,
        payment_term=term,
        user_id=user.id,
        quote_number=81003,
        activated_at=T - timedelta(days=1),
        valid_until=T + timedelta(days=5),
        price=Decimal("5.10"),
        minimum_volume=Decimal("20000"),
    )
    # D: antes de T, elegível e mais barata → melhor
    qd, id_ = await _quote_with_item(
        db=db_session,
        org_id=org.id,
        station_id=headquarters.id,
        distributor_id=dist_d.id,
        product_id=product.id,
        payment_term=term,
        user_id=user.id,
        quote_number=81004,
        activated_at=T - timedelta(hours=6),
        valid_until=T + timedelta(days=5),
        price=Decimal("5.80"),
        minimum_volume=Decimal("1000"),
    )

    invoice = FuelPurchaseInvoice(
        organization_id=org.id,
        station_id=headquarters.id,
        source_invoice_id="INV-8101",
        source_document_number="8101",
        source_series="1",
        source_supplier_id="SUP1",
        distributor_id=dist_a.id,
        issue_date=date(2026, 7, 9),
        entry_date=date(2026, 7, 9),
        operation_type="PURCHASE",
        source_status="ACTIVE",
        is_cancelled=False,
        gross_amount=Decimal("24000"),
        discount_amount=Decimal("0"),
        freight_amount=Decimal("0"),
        insurance_amount=Decimal("0"),
        other_expenses_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("24000"),
        metric_eligibility_status="INCLUDED",
        source_record_hash="h1",
    )
    db_session.add(invoice)
    await db_session.flush()

    item = FuelPurchaseItem(
        organization_id=org.id,
        station_id=headquarters.id,
        purchase_invoice_id=invoice.id,
        source_invoice_id="INV-8101",
        source_invoice_item_id="1",
        source_product_id="P1",
        canonical_product_id=product.id,
        source_unit="L",
        source_quantity=Decimal("4000"),
        volume_liters=Decimal("4000"),
        unit_price=Decimal("6.00"),
        gross_item_amount=Decimal("24000"),
        discount_amount=Decimal("0"),
        rebate_amount=Decimal("0"),
        allocated_freight_amount=Decimal("0"),
        allocated_insurance_amount=Decimal("0"),
        allocated_other_expenses=Decimal("0"),
        commercial_delivered_cost=Decimal("24000"),
        delivered_cost_per_liter=Decimal("6.00000000"),
        operation_type="PURCHASE",
        is_cancelled=False,
        metric_eligibility_status="INCLUDED",
        source_record_hash="hi1",
    )
    db_session.add(item)
    await db_session.flush()

    # Força T = 09/07/2026 10:00 (cenário E2E exigido; emissão sozinha seria 00:00).
    db_session.add(
        PurchaseBenchmarkOverride(
            organization_id=org.id,
            purchase_invoice_id=invoice.id,
            override_type=BenchmarkOverrideType.REFERENCE_DATETIME,
            previous_value=None,
            new_value={"reference_datetime": T.isoformat()},
            reason="E2E no-hindsight Sprint 8.1 — T controlado",
            created_by=user.id,
            created_at=T,
        )
    )
    await db_session.flush()

    run = await PurchaseQuoteBenchmarkService(db_session).run_for_invoice(
        organization_id=org.id,
        invoice_id=invoice.id,
        station_ids=[headquarters.id],
        requested_by=user.id,
    )
    await db_session.flush()

    assert run.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "PARTIAL"}
    assert run.reference_datetime == T
    assert run.snapshot_hash

    items = list(
        (
            await db_session.execute(
                select(PurchaseQuoteBenchmarkItem).where(
                    PurchaseQuoteBenchmarkItem.benchmark_run_id == run.id
                )
            )
        ).scalars().all()
    )
    assert len(items) == 1
    bi = items[0]
    assert bi.benchmark_status in {
        BenchmarkItemStatus.BENCHMARKED,
        BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS,
    }
    assert bi.best_quote_id == qd.id
    assert bi.best_quote_item_id == id_.id
    assert bi.volume_liters == Decimal("4000")
    assert bi.actual_delivered_cost_per_liter == Decimal("6.00000000")
    assert bi.benchmark_cost_per_liter == Decimal("5.80000000")
    assert bi.cost_variance_per_liter == Decimal("0.20000000")
    assert bi.opportunity_amount == Decimal("800.0000")
    assert bi.actual_advantage_amount == Decimal("0.0000")
    assert bi.decision_result == BenchmarkDecisionResult.ABOVE_BEST

    cands = list(
        (
            await db_session.execute(
                select(PurchaseQuoteBenchmarkCandidate).where(
                    PurchaseQuoteBenchmarkCandidate.benchmark_item_id == bi.id
                )
            )
        ).scalars().all()
    )
    quote_ids = {c.quote_id for c in cands}
    assert qb.id not in quote_ids, "cotação futura não pode ser candidata"
    assert qa.id in quote_ids
    assert qc.id in quote_ids
    assert qd.id in quote_ids

    cand_c = next(c for c in cands if c.quote_id == qc.id)
    assert cand_c.eligibility_status == EligibilityStatus.INELIGIBLE
    assert cand_c.is_best is False
    codes = {r.get("code") for r in (cand_c.blocking_reasons or [])}
    assert "MINIMUM_VOLUME_NOT_REACHED" in codes

    cand_d = next(c for c in cands if c.quote_id == qd.id)
    assert cand_d.is_best is True
    assert cand_d.ranking_position == 1

    # snapshot contém candidatos / bloqueios / ranking
    assert bi.result_snapshot is not None
    assert bi.input_snapshot is not None
    assert run.output_snapshot is not None
    assert "items" in run.output_snapshot
    assert bi.snapshot_hash

    # nenhum activated_at futuro
    for c in cands:
        qrow = (await db_session.execute(select(Quote).where(Quote.id == c.quote_id))).scalar_one()
        assert qrow.activated_at is not None
        assert qrow.activated_at <= run.reference_datetime

    # reprocessamento imutável
    original_hash = run.snapshot_hash
    original_id = run.id
    run2 = await PurchaseQuoteBenchmarkService(db_session).reprocess(
        organization_id=org.id,
        run_id=run.id,
        station_ids=[headquarters.id],
        requested_by=user.id,
        reason="Idempotência Sprint 8.1",
    )
    await db_session.flush()
    assert run2.id != original_id
    assert run2.reprocess_of_run_id == original_id
    assert run2.snapshot_hash == original_hash

    original = (
        await db_session.execute(
            select(PurchaseQuoteBenchmarkRun).where(PurchaseQuoteBenchmarkRun.id == original_id)
        )
    ).scalar_one()
    assert original.snapshot_hash == original_hash
