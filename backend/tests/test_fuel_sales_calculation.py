"""Testes de cálculo de vendas combustível."""

from decimal import Decimal

from app.services.fuel_sales_calculation_service import (
    compute_margin,
    compute_net_amount,
    compute_realized_price_per_liter,
    compute_total_cost,
)


def test_realized_price_from_net_and_volume() -> None:
    price = compute_realized_price_per_liter(Decimal("1000"), Decimal("200"))
    assert price == Decimal("5")


def test_net_amount_from_source() -> None:
    net, origin = compute_net_amount(source_net=Decimal("50"), gross=None, discount=None, surcharge=None)
    assert net == Decimal("50")
    assert origin == "SOURCE_NET"


def test_margin_unavailable_without_cost() -> None:
    result = compute_margin(net_amount=Decimal("100"), total_cost=None, volume_liters=Decimal("10"))
    assert result["margin_status"] == "UNAVAILABLE"


def test_margin_negative_preserved() -> None:
    result = compute_margin(net_amount=Decimal("100"), total_cost=Decimal("150"), volume_liters=Decimal("10"))
    assert result["gross_margin_amount"] == Decimal("-50")
    assert result["gross_margin_per_liter"] == Decimal("-5")


def test_total_cost_from_per_liter() -> None:
    total, source, mismatch = compute_total_cost(
        source_total_cost=None, cost_per_liter=Decimal("4.5"), volume_liters=Decimal("100")
    )
    assert total == Decimal("450")
    assert source == "ERP_RECORDED_COST"
    assert mismatch is False
