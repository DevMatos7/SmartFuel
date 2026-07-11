"""Política explícita de CFOP — natureza fiscal separada da elegibilidade de combustível."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CfopTreatment(StrEnum):
    """Tratamento persistido em fuel_sales_facts.cfop_classification."""

    INCLUDE_AS_SALE = "INCLUDE_AS_SALE"
    INCLUDE_AS_SALE_GENERAL = "INCLUDE_AS_SALE_GENERAL"
    INCLUDE_AS_SALE_GENERAL_ST = "INCLUDE_AS_SALE_GENERAL_ST"
    INCLUDE_AS_RETURN = "INCLUDE_AS_RETURN"
    EXCLUDE_NON_COMMERCIAL = "EXCLUDE_NON_COMMERCIAL"
    PENDING_REVIEW = "PENDING_REVIEW"


class CfopOperationClass(StrEnum):
    SALE = "SALE"
    RETURN = "RETURN"
    NON_COMMERCIAL = "NON_COMMERCIAL"
    UNKNOWN = "UNKNOWN"


class CfopAnalyticsScope(StrEnum):
    FUEL_CANDIDATE = "FUEL_CANDIDATE"
    NON_FUEL_BY_DEFAULT = "NON_FUEL_BY_DEFAULT"
    EXCLUDED = "EXCLUDED"
    PENDING = "PENDING"


class CfopReviewStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    PROVISIONAL_FISCAL_CONFIRMATION = "PROVISIONAL_FISCAL_CONFIRMATION"
    PENDING_REVIEW = "PENDING_REVIEW"


@dataclass(frozen=True)
class CfopPolicy:
    operation_class: str
    fiscal_category: str
    default_analytics_scope: str
    review_status: str
    treatment: CfopTreatment

    @property
    def is_sale(self) -> bool:
        return self.operation_class == CfopOperationClass.SALE

    @property
    def is_fuel_candidate(self) -> bool:
        return self.default_analytics_scope == CfopAnalyticsScope.FUEL_CANDIDATE

    @property
    def is_non_fuel_by_default(self) -> bool:
        return self.default_analytics_scope == CfopAnalyticsScope.NON_FUEL_BY_DEFAULT

    @property
    def requires_pending_review(self) -> bool:
        return (
            self.treatment == CfopTreatment.PENDING_REVIEW
            or self.default_analytics_scope == CfopAnalyticsScope.PENDING
        )


def normalize_cfop(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace(" ", "")


def _digits(cfop: str) -> str:
    return "".join(ch for ch in cfop if ch.isdigit())


PENDING_POLICY = CfopPolicy(
    operation_class=CfopOperationClass.UNKNOWN,
    fiscal_category="UNCLASSIFIED",
    default_analytics_scope=CfopAnalyticsScope.PENDING,
    review_status=CfopReviewStatus.PENDING_REVIEW,
    treatment=CfopTreatment.PENDING_REVIEW,
)

# Chaves normalizadas com e sem ponto (5.656 / 5656).
CFOP_POLICIES: dict[str, CfopPolicy] = {
    "5656": CfopPolicy(
        operation_class=CfopOperationClass.SALE,
        fiscal_category="FUEL_OR_LUBRICANT",
        default_analytics_scope=CfopAnalyticsScope.FUEL_CANDIDATE,
        review_status=CfopReviewStatus.CONFIRMED,
        treatment=CfopTreatment.INCLUDE_AS_SALE,
    ),
    "5667": CfopPolicy(
        operation_class=CfopOperationClass.SALE,
        fiscal_category="FUEL_OR_LUBRICANT",
        default_analytics_scope=CfopAnalyticsScope.FUEL_CANDIDATE,
        review_status=CfopReviewStatus.CONFIRMED,
        treatment=CfopTreatment.INCLUDE_AS_SALE,
    ),
    "5102": CfopPolicy(
        operation_class=CfopOperationClass.SALE,
        fiscal_category="GENERAL_MERCHANDISE",
        default_analytics_scope=CfopAnalyticsScope.NON_FUEL_BY_DEFAULT,
        review_status=CfopReviewStatus.PROVISIONAL_FISCAL_CONFIRMATION,
        treatment=CfopTreatment.INCLUDE_AS_SALE_GENERAL,
    ),
    "5405": CfopPolicy(
        operation_class=CfopOperationClass.SALE,
        fiscal_category="GENERAL_MERCHANDISE_ST",
        default_analytics_scope=CfopAnalyticsScope.NON_FUEL_BY_DEFAULT,
        review_status=CfopReviewStatus.PROVISIONAL_FISCAL_CONFIRMATION,
        treatment=CfopTreatment.INCLUDE_AS_SALE_GENERAL_ST,
    ),
}

# Aliases com ponto para lookup direto.
for _digits_key, _policy in list(CFOP_POLICIES.items()):
    if len(_digits_key) == 4:
        CFOP_POLICIES[f"{_digits_key[0]}.{_digits_key[1:]}"] = _policy


def get_cfop_policy(cfop: str | None) -> CfopPolicy:
    key = normalize_cfop(cfop)
    if key is None:
        return PENDING_POLICY
    if key in CFOP_POLICIES:
        return CFOP_POLICIES[key]
    digits = _digits(key)
    if digits in CFOP_POLICIES:
        return CFOP_POLICIES[digits]
    return PENDING_POLICY


def classify_cfop(cfop: str | None) -> CfopTreatment:
    """Compatibilidade: retorna o treatment persistível."""
    return get_cfop_policy(cfop).treatment


def cfop_excluded_from_kpis(treatment: CfopTreatment) -> bool:
    """Bloqueio estrito no nível CFOP (antes da análise de produto)."""
    return treatment in (
        CfopTreatment.PENDING_REVIEW,
        CfopTreatment.EXCLUDE_NON_COMMERCIAL,
    )


def treatment_from_stored(value: str | None) -> CfopTreatment | None:
    if not value:
        return None
    try:
        return CfopTreatment(value)
    except ValueError:
        return None
