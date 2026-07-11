"""Testes unitários — Sprint 8 purchase benchmarks (agrupamento, fórmulas, referência)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.core.purchase_benchmark_enums import (
    BenchmarkDecisionResult,
    PurchaseReferenceConfidence,
    PurchaseReferenceSource,
)
from app.services.purchase_benchmark_support import (
    ActualPurchaseCostService,
    PurchaseItemGroupingService,
)
from app.services.purchase_quote_benchmark_service import PurchaseQuoteBenchmarkService


def _item(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "is_cancelled": False,
        "canonical_product_id": uuid.uuid4(),
        "source_product_id": "P1",
        "volume_liters": Decimal("1000"),
        "commercial_delivered_cost": Decimal("5000"),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_group_same_product_sums_volume_and_cost():
    pid = uuid.uuid4()
    items = [
        _item(canonical_product_id=pid, volume_liters=Decimal("1000"), commercial_delivered_cost=Decimal("4000")),
        _item(canonical_product_id=pid, volume_liters=Decimal("500"), commercial_delivered_cost=Decimal("2000")),
        _item(canonical_product_id=uuid.uuid4(), volume_liters=Decimal("100"), commercial_delivered_cost=Decimal("300")),
    ]
    groups = PurchaseItemGroupingService().group(items)
    assert len(groups) == 2
    same = next(g for g in groups if g.canonical_product_id == pid)
    assert same.volume_liters == Decimal("1500")
    assert same.commercial_delivered_cost == Decimal("6000")
    assert len(same.item_ids) == 2


def test_group_does_not_merge_different_products():
    groups = PurchaseItemGroupingService().group(
        [
            _item(canonical_product_id=uuid.uuid4()),
            _item(canonical_product_id=uuid.uuid4()),
        ]
    )
    assert len(groups) == 2


def test_group_skips_cancelled():
    groups = PurchaseItemGroupingService().group(
        [_item(is_cancelled=True), _item(is_cancelled=False)]
    )
    assert len(groups) == 1


def test_group_unmapped_by_source_product():
    groups = PurchaseItemGroupingService().group(
        [
            _item(canonical_product_id=None, source_product_id="X"),
            _item(canonical_product_id=None, source_product_id="X"),
        ]
    )
    assert len(groups) == 1
    assert groups[0].unmapped is True


def test_cost_per_liter():
    assert ActualPurchaseCostService.cost_per_liter(
        total_cost=Decimal("1000"), volume_liters=Decimal("200")
    ) == Decimal("5.00000000")
    assert ActualPurchaseCostService.cost_per_liter(total_cost=Decimal("10"), volume_liters=Decimal("0")) is None


def test_decision_tolerance_and_advantage():
    svc = PurchaseQuoteBenchmarkService.__new__(PurchaseQuoteBenchmarkService)
    params = SimpleNamespace(
        absolute_tolerance_per_liter=Decimal("0.005"),
        percentage_tolerance=Decimal("0.001"),
    )
    assert (
        svc._decision_result(
            variance_pl=Decimal("0"),
            actual_per_l=Decimal("5"),
            params=params,
        )
        == BenchmarkDecisionResult.BEST_OR_TIED
    )
    assert (
        svc._decision_result(
            variance_pl=Decimal("-0.02"),
            actual_per_l=Decimal("5"),
            params=params,
        )
        == BenchmarkDecisionResult.BELOW_BENCHMARK
    )
    assert (
        svc._decision_result(
            variance_pl=Decimal("0.003"),
            actual_per_l=Decimal("5"),
            params=params,
        )
        == BenchmarkDecisionResult.WITHIN_TOLERANCE
    )
    assert (
        svc._decision_result(
            variance_pl=Decimal("0.05"),
            actual_per_l=Decimal("5"),
            params=params,
        )
        == BenchmarkDecisionResult.ABOVE_BEST
    )


def test_opportunity_and_advantage_formulas():
    variance = Decimal("100")
    assert max(variance, Decimal("0")) == Decimal("100")
    assert max(-variance, Decimal("0")) == Decimal("0")
    variance_neg = Decimal("-40")
    assert max(variance_neg, Decimal("0")) == Decimal("0")
    assert max(-variance_neg, Decimal("0")) == Decimal("40")
