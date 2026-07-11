"""Testes da política de CFOP × produto × unidade — Sprint 6."""

from __future__ import annotations

from decimal import Decimal

from app.core.cfop_policy import (
    CfopAnalyticsScope,
    CfopReviewStatus,
    CfopTreatment,
    classify_cfop,
    cfop_excluded_from_kpis,
    get_cfop_policy,
)
from app.core.fuel_sales_enums import MarginStatus, MetricEligibilityStatus, MetricExclusionReason
from app.core.master_data_enums import MappingStatus
from app.models.erp_product import ErpProduct
from app.services.fuel_sales_apply_service import _compute_eligibility, _resolve_volume_liters


def test_cfop_5667_is_confirmed_fuel_candidate():
    policy = get_cfop_policy("5.667")
    assert policy.treatment == CfopTreatment.INCLUDE_AS_SALE
    assert policy.is_fuel_candidate
    assert policy.review_status == CfopReviewStatus.CONFIRMED
    assert classify_cfop("5667") == CfopTreatment.INCLUDE_AS_SALE
    assert not cfop_excluded_from_kpis(CfopTreatment.INCLUDE_AS_SALE)


def test_cfop_5102_is_general_sale_not_fuel_by_default():
    policy = get_cfop_policy("5.102")
    assert policy.treatment == CfopTreatment.INCLUDE_AS_SALE_GENERAL
    assert policy.is_sale
    assert policy.is_non_fuel_by_default
    assert policy.fiscal_category == "GENERAL_MERCHANDISE"
    assert policy.review_status == CfopReviewStatus.PROVISIONAL_FISCAL_CONFIRMATION
    assert not cfop_excluded_from_kpis(policy.treatment)


def test_cfop_5405_is_general_sale_st_provisional():
    policy = get_cfop_policy("5.405")
    assert policy.treatment == CfopTreatment.INCLUDE_AS_SALE_GENERAL_ST
    assert policy.is_sale
    assert policy.is_non_fuel_by_default
    assert policy.fiscal_category == "GENERAL_MERCHANDISE_ST"


def test_unknown_cfop_remains_pending_review():
    policy = get_cfop_policy("9.999")
    assert policy.treatment == CfopTreatment.PENDING_REVIEW
    assert policy.requires_pending_review
    assert cfop_excluded_from_kpis(CfopTreatment.PENDING_REVIEW)


def test_volume_liters_from_l_unit():
    volume, reason = _resolve_volume_liters(Decimal("10"), "L", analytics_scope=CfopAnalyticsScope.FUEL_CANDIDATE)
    assert volume == Decimal("10")
    assert reason is None


def test_volume_ml_converts_to_liters():
    volume, reason = _resolve_volume_liters(Decimal("200"), "ML", analytics_scope=CfopAnalyticsScope.NON_FUEL_BY_DEFAULT)
    assert volume == Decimal("0.2")
    assert reason is None


def test_volume_un_requires_conversion():
    volume, reason = _resolve_volume_liters(Decimal("1"), "UN", analytics_scope=CfopAnalyticsScope.NON_FUEL_BY_DEFAULT)
    assert volume is None
    assert reason == MetricExclusionReason.UNIT_CONVERSION_REQUIRED


def test_null_unit_assumes_liters_only_for_fuel_candidate_cfop():
    volume, reason = _resolve_volume_liters(Decimal("60"), None, analytics_scope=CfopAnalyticsScope.FUEL_CANDIDATE)
    assert volume == Decimal("60")
    assert reason is None

    volume2, reason2 = _resolve_volume_liters(Decimal("1"), None, analytics_scope=CfopAnalyticsScope.NON_FUEL_BY_DEFAULT)
    assert volume2 is None
    assert reason2 == MetricExclusionReason.UNIT_CONVERSION_REQUIRED


def _eligibility(**overrides):
    erp_product = overrides.pop("erp_product", ErpProduct(mapping_status=MappingStatus.MAPPED))
    params = {
        "is_cancelled": False,
        "erp_product": erp_product,
        "volume_liters": Decimal("10"),
        "volume_reason": None,
        "net_amount": Decimal("100"),
        "cost_mismatch": False,
        "payment_method_group": None,
        "source_payment_method_id": None,
        "margin_status": MarginStatus.AVAILABLE,
        "gross_margin_amount": Decimal("5"),
        "cfop_policy": get_cfop_policy("5.656"),
        "operation_type": "SALE",
        "is_fuel_product": True,
        "missing_erp_product": False,
    }
    params.update(overrides)
    return _compute_eligibility(**params)


def test_fuel_cfop_mapped_fuel_product_eligible():
    status, reasons = _eligibility()
    assert status == MetricEligibilityStatus.ELIGIBLE
    assert reasons == []


def test_5102_with_fuel_product_not_auto_eligible():
    """5.102 + combustível mapeado + L: não liberar só pelo CFOP — escopo NON_FUEL_BY_DEFAULT."""
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("5.102"),
        is_fuel_product=True,
        volume_liters=Decimal("10"),
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.EXCLUDED_NON_FUEL_PRODUCT]


def test_5102_non_fuel_product_excluded_from_fuel_kpis():
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("5.102"),
        is_fuel_product=False,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.EXCLUDED_NON_FUEL_PRODUCT]


def test_5102_pending_product_preserved_out_of_kpis():
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("5.102"),
        erp_product=ErpProduct(mapping_status=MappingStatus.PENDING),
        is_fuel_product=False,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.UNMAPPED_PRODUCT]


def test_5102_unit_un_requires_conversion():
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("5.102"),
        is_fuel_product=False,
        volume_liters=None,
        volume_reason=MetricExclusionReason.UNIT_CONVERSION_REQUIRED,
    )
    # Produto não combustível / CFOP geral tem precedência sobre unidade.
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.EXCLUDED_NON_FUEL_PRODUCT]


def test_fuel_candidate_with_unit_un_requires_conversion():
    status, reasons = _eligibility(
        volume_liters=None,
        volume_reason=MetricExclusionReason.UNIT_CONVERSION_REQUIRED,
        is_fuel_product=True,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.UNIT_CONVERSION_REQUIRED]


def test_5405_general_merchandise_out_of_fuel_kpis():
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("5.405"),
        is_fuel_product=False,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.EXCLUDED_NON_FUEL_PRODUCT]


def test_unknown_cfop_pending_classification():
    status, reasons = _eligibility(
        cfop_policy=get_cfop_policy("9.999"),
        is_fuel_product=True,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.PENDING_CFOP_CLASSIFICATION]


def test_cancelled_sale_excluded_by_cancellation_even_with_pending_cfop():
    status, reasons = _eligibility(
        is_cancelled=True,
        cfop_policy=get_cfop_policy("9.999"),
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.CANCELLED_SALE]


def test_missing_erp_product_reference_excluded_not_blocking():
    status, reasons = _eligibility(
        erp_product=None,
        missing_erp_product=True,
        cfop_policy=get_cfop_policy("5.102"),
        is_fuel_product=False,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert MetricExclusionReason.MISSING_ERP_PRODUCT_REFERENCE in reasons
    assert MetricExclusionReason.EXCLUDED_NON_FUEL_PRODUCT in reasons
    assert MetricExclusionReason.UNMAPPED_PRODUCT not in reasons


def test_missing_erp_product_on_fuel_cfop_still_excluded():
    status, reasons = _eligibility(
        erp_product=None,
        missing_erp_product=True,
        cfop_policy=get_cfop_policy("5.656"),
        is_fuel_product=False,
    )
    assert status == MetricEligibilityStatus.EXCLUDED
    assert reasons == [MetricExclusionReason.MISSING_ERP_PRODUCT_REFERENCE]
