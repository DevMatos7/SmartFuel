"""Testes unitários do domínio de comparação de cotações — Sprint 4.1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.quote_comparison_enums import EligibilityStatus
from app.domain.quote_comparison.eligibility import make_reason, resolve_eligibility_status
from app.domain.quote_comparison.formulas import (
    compute_daily_rate,
    compute_delivered_cost_per_liter,
    compute_financial_equivalent_cost_per_liter,
    compute_freight_per_liter,
    compute_total,
)
from app.domain.quote_comparison.constants import LITER_PERSIST_SCALE, RATE_PERSIST_SCALE, TOTAL_PERSIST_SCALE
from app.domain.quote_comparison.ranking import RankableOffer, sort_offers
from app.domain.quote_comparison.snapshot_canonical import canonical_json_dumps, compute_snapshot_hash
from app.services.quote_candidate_service import QuoteCandidateService
from app.services.quote_ranking_service import ProcessedOffer, QuoteRankingService
from app.services.quote_spread_service import QuoteSpreadService


def test_daily_rate_zero_returns_zero() -> None:
    assert compute_daily_rate(annual_effective_rate=Decimal("0"), day_count_basis=365) == Decimal("0")


def test_daily_rate_15_percent_known_value() -> None:
    rate = compute_daily_rate(annual_effective_rate=Decimal("0.15"), day_count_basis=365)
    simple = Decimal("0.15") / Decimal("365")
    assert rate > Decimal("0")
    assert rate < simple
    expected = (Decimal("1") + Decimal("0.15")) ** (Decimal("1") / Decimal("365")) - Decimal("1")
    assert rate == expected.quantize(RATE_PERSIST_SCALE)


def test_financial_equivalent_21_days_with_15_percent() -> None:
    delivered = Decimal("5.29500000")
    daily = compute_daily_rate(annual_effective_rate=Decimal("0.15"), day_count_basis=365)
    equivalent = compute_financial_equivalent_cost_per_liter(
        delivered_cost_per_liter=delivered,
        daily_rate=daily,
        financial_days=21,
    )
    assert equivalent < delivered
    divisor = (Decimal("1") + daily) ** 21
    expected = (delivered / divisor).quantize(LITER_PERSIST_SCALE)
    assert equivalent == expected


def test_financial_equivalent_zero_days_equals_delivered() -> None:
    delivered = Decimal("5.30")
    assert compute_financial_equivalent_cost_per_liter(
        delivered_cost_per_liter=delivered,
        daily_rate=Decimal("0.00038212"),
        financial_days=0,
    ) == delivered


def test_freight_total_with_decimal_volume() -> None:
    freight = compute_freight_per_liter(
        freight_calculation_type="TOTAL",
        freight_value_per_liter=None,
        freight_value_total=Decimal("1500.50"),
        requested_volume_liters=Decimal("12500.500"),
    )
    expected = (Decimal("1500.50") / Decimal("12500.500")).quantize(LITER_PERSIST_SCALE)
    assert freight == expected


def test_delivered_cost_allows_negative_formula_result() -> None:
    delivered = compute_delivered_cost_per_liter(
        quoted_price_per_liter=Decimal("5.00"),
        discount_per_liter=Decimal("6.00"),
        rebate_per_liter=Decimal("0"),
        freight_per_liter=Decimal("0"),
        other_cost_per_liter=Decimal("0"),
    )
    assert delivered == Decimal("-1.00000000")


def test_total_rounding_half_up() -> None:
    total = compute_total(cost_per_liter=Decimal("5.18324567"), requested_volume_liters=Decimal("30000"))
    expected = (Decimal("5.18324567") * Decimal("30000")).quantize(TOTAL_PERSIST_SCALE)
    assert total == expected


def test_snapshot_hash_is_deterministic_for_key_order() -> None:
    payload_a = {"b": "2", "a": {"z": 1, "y": 2}, "results": [{"id": "1"}, {"id": "2"}]}
    payload_b = {"results": [{"id": "1"}, {"id": "2"}], "a": {"y": 2, "z": 1}, "b": "2"}
    assert compute_snapshot_hash(payload_a) == compute_snapshot_hash(payload_b)


def test_snapshot_hash_changes_when_result_changes() -> None:
    base = {"input": {"volume": "1000"}, "results": [{"cost": "5.20"}]}
    changed = {"input": {"volume": "1000"}, "results": [{"cost": "5.21"}]}
    assert compute_snapshot_hash(base) != compute_snapshot_hash(changed)


def test_canonical_json_normalizes_decimal() -> None:
    payload = {"rate": Decimal("0.15000000")}
    dumped = canonical_json_dumps(payload)
    assert '"rate":"0.15000000"' in dumped or '"rate": "0.15000000"' in dumped.replace(" ", "")


def test_quote_known_at_boundary() -> None:
    service = QuoteCandidateService(db=None)  # type: ignore[arg-type]
    activated = datetime(2026, 7, 10, 9, 0, tzinfo=UTC)
    comparison = datetime(2026, 7, 10, 9, 0, tzinfo=UTC)

    class Quote:
        activated_at = activated

    assert service.was_quote_known_at(Quote(), comparison) is True


def test_item_invalid_at_exact_valid_until() -> None:
    service = QuoteCandidateService(db=None)  # type: ignore[arg-type]
    boundary = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    comparison = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)

    class Item:
        valid_until = boundary

    class Quote:
        valid_until = boundary

    assert service.was_item_valid_at(Item(), Quote(), comparison) is False


def test_spread_counts_separate_eligible_and_warning() -> None:
    dist = uuid.uuid4()
    offers = [
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=dist,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            raw_price_per_liter=Decimal("5.20"),
            delivered_cost_per_liter=Decimal("5.20"),
            financial_equivalent_cost_per_liter=Decimal("5.20"),
            ranking_cost_per_liter=Decimal("5.20"),
            rank_position=1,
        ),
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            eligibility_status=EligibilityStatus.ELIGIBLE_WITH_WARNINGS,
            raw_price_per_liter=Decimal("5.30"),
            delivered_cost_per_liter=Decimal("5.30"),
            financial_equivalent_cost_per_liter=Decimal("5.30"),
            ranking_cost_per_liter=Decimal("5.30"),
            rank_position=2,
        ),
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            eligibility_status=EligibilityStatus.INELIGIBLE,
            raw_price_per_liter=Decimal("5.10"),
            delivered_cost_per_liter=Decimal("5.10"),
            financial_equivalent_cost_per_liter=Decimal("5.10"),
            ranking_cost_per_liter=None,
            rank_position=None,
        ),
    ]
    summary = QuoteSpreadService().compute(offers)
    assert summary.eligible_count == 1
    assert summary.warning_count == 1
    assert summary.ineligible_count == 1
    assert summary.spread_absolute == Decimal("0.10000000")


def test_best_per_distributor_excludes_secondary_offers_from_spread_pool() -> None:
    dist = uuid.uuid4()
    ranking = QuoteRankingService()
    offers = [
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=dist,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            raw_price_per_liter=Decimal("5.10"),
            delivered_cost_per_liter=Decimal("5.10"),
            financial_equivalent_cost_per_liter=Decimal("5.10"),
            ranking_cost_per_liter=Decimal("5.10"),
            distributor_name="A",
            activated_at=datetime.now(UTC),
            effective_valid_until=datetime.now(UTC) + timedelta(days=1),
        ),
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=dist,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            raw_price_per_liter=Decimal("5.50"),
            delivered_cost_per_liter=Decimal("5.50"),
            financial_equivalent_cost_per_liter=Decimal("5.50"),
            ranking_cost_per_liter=Decimal("5.50"),
            distributor_name="A",
            activated_at=datetime.now(UTC),
            effective_valid_until=datetime.now(UTC) + timedelta(days=1),
        ),
        ProcessedOffer(
            quote_id=uuid.uuid4(),
            quote_item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            eligibility_status=EligibilityStatus.ELIGIBLE,
            raw_price_per_liter=Decimal("5.30"),
            delivered_cost_per_liter=Decimal("5.30"),
            financial_equivalent_cost_per_liter=Decimal("5.30"),
            ranking_cost_per_liter=Decimal("5.30"),
            distributor_name="B",
            activated_at=datetime.now(UTC),
            effective_valid_until=datetime.now(UTC) + timedelta(days=1),
        ),
    ]
    ranked = ranking.apply_ranking(
        offers,
        ranking_mode="DELIVERED",
        ranking_scope="BEST_PER_DISTRIBUTOR",
        requested_volume_liters=Decimal("10000"),
    )
    summary = QuoteSpreadService().compute(ranked)
    assert summary.distributor_count == 2
    assert summary.best_cost_per_liter == Decimal("5.10000000")
    assert summary.highest_cost_per_liter == Decimal("5.30000000")


def test_ranking_tie_break_by_delivery_then_name() -> None:
    base = datetime(2026, 7, 10, tzinfo=UTC)
    offers = [
        RankableOffer(
            item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            distributor_name="Beta",
            ranking_cost=Decimal("5.30"),
            financial_equivalent_cost=Decimal("5.30"),
            delivered_cost=Decimal("5.30"),
            raw_price=Decimal("5.20"),
            delivery_expected_at=base + timedelta(hours=8),
            effective_valid_until=base + timedelta(days=1),
            activated_at=base,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        ),
        RankableOffer(
            item_id=uuid.uuid4(),
            distributor_id=uuid.uuid4(),
            distributor_name="Alpha",
            ranking_cost=Decimal("5.30"),
            financial_equivalent_cost=Decimal("5.30"),
            delivered_cost=Decimal("5.30"),
            raw_price=Decimal("5.20"),
            delivery_expected_at=base + timedelta(hours=6),
            effective_valid_until=base + timedelta(days=1),
            activated_at=base,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        ),
    ]
    ordered = sort_offers(offers)
    assert ordered[0].distributor_name == "Alpha"


def test_eligibility_status_with_blocking_and_warning() -> None:
    reasons = [
        make_reason("AVAILABLE_VOLUME_NOT_INFORMED", severity="WARNING"),
        make_reason("MINIMUM_VOLUME_NOT_REACHED", severity="BLOCKING"),
    ]
    assert resolve_eligibility_status(reasons) == EligibilityStatus.INELIGIBLE
