from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.master_data_enums import PaymentType, RuleSource
from app.core.quote_comparison_enums import EligibilityStatus, RankingMode, ReasonSeverity
from app.domain.quote_comparison.eligibility import EligibilityReason, make_reason, resolve_eligibility_status
from app.models.financial_parameter import FinancialParameter
from app.services.quote_candidate_service import QuoteCandidate, QuoteCandidateService
from app.services.supplier_rule_service import EffectiveRuleResult


@dataclass
class ComparisonScenario:
    organization_id: uuid.UUID
    station_id: uuid.UUID
    product_id: uuid.UUID
    requested_volume_liters: Decimal
    comparison_datetime: datetime
    required_delivery_at: datetime | None
    ranking_mode: str


class QuoteEligibilityService:
    NEAR_EXPIRATION_WINDOW = timedelta(hours=1)
    LOW_MARGIN_RATIO = Decimal("0.05")

    def __init__(self, candidate_service: QuoteCandidateService) -> None:
        self.candidate_service = candidate_service

    def evaluate(
        self,
        candidate: QuoteCandidate,
        *,
        scenario: ComparisonScenario,
        rule: EffectiveRuleResult,
        financial_parameter: FinancialParameter | None,
        delivered_cost_per_liter: Decimal | None,
    ) -> tuple[str, list[EligibilityReason]]:
        reasons: list[EligibilityReason] = []
        quote = candidate.quote
        item = candidate.item
        comp = scenario.comparison_datetime

        if quote.organization_id != scenario.organization_id:
            reasons.append(make_reason("CROSS_ORGANIZATION_REFERENCE", severity=ReasonSeverity.BLOCKING))
        if quote.station_id != scenario.station_id:
            reasons.append(make_reason("STATION_NOT_ALLOWED", severity=ReasonSeverity.BLOCKING))
        if item.product_id != scenario.product_id:
            reasons.append(make_reason("PRODUCT_NOT_ALLOWED", severity=ReasonSeverity.BLOCKING))

        if not self.candidate_service.was_quote_known_at(quote, comp):
            reasons.append(make_reason("QUOTE_NOT_KNOWN_AT_COMPARISON_TIME", severity=ReasonSeverity.BLOCKING))
        elif not self.candidate_service.was_quote_active_at(quote, comp):
            if quote.cancelled_at and quote.cancelled_at <= comp:
                reasons.append(make_reason("QUOTE_NOT_ACTIVE_AT_COMPARISON_TIME", severity=ReasonSeverity.BLOCKING))
            elif quote.superseded_at and quote.superseded_at <= comp:
                reasons.append(make_reason("QUOTE_NOT_ACTIVE_AT_COMPARISON_TIME", severity=ReasonSeverity.BLOCKING))
            else:
                reasons.append(make_reason("QUOTE_EXPIRED", severity=ReasonSeverity.BLOCKING))

        if not self.candidate_service.was_item_valid_at(item, quote, comp):
            reasons.append(make_reason("ITEM_EXPIRED", severity=ReasonSeverity.BLOCKING))

        if not rule.allowed:
            reasons.append(
                make_reason(
                    "SUPPLIER_NOT_ALLOWED",
                    severity=ReasonSeverity.BLOCKING,
                    metadata={"reason": rule.reason, "rule_source": rule.rule_source},
                )
            )

        if rule.rule_source == RuleSource.ORGANIZATION_DEFAULT:
            reasons.append(make_reason("SUPPLIER_RULE_NOT_EXPLICIT", severity=ReasonSeverity.WARNING))

        effective_base_id = item.distribution_base_id or quote.distribution_base_id
        if rule.distribution_base_id is not None:
            if effective_base_id is None:
                reasons.append(make_reason("BASE_NOT_INFORMED", severity=ReasonSeverity.BLOCKING))
            elif effective_base_id != rule.distribution_base_id:
                reasons.append(make_reason("BASE_NOT_ALLOWED", severity=ReasonSeverity.BLOCKING))
        elif effective_base_id is None:
            reasons.append(make_reason("BASE_NOT_INFORMED", severity=ReasonSeverity.WARNING))

        minimum_volume = item.minimum_volume_liters or rule.minimum_volume_liters
        if scenario.requested_volume_liters < minimum_volume:
            reasons.append(
                make_reason(
                    "MINIMUM_VOLUME_NOT_REACHED",
                    severity=ReasonSeverity.BLOCKING,
                    metadata={
                        "requested_volume_liters": str(scenario.requested_volume_liters),
                        "minimum_volume_liters": str(minimum_volume),
                        "difference_liters": str(minimum_volume - scenario.requested_volume_liters),
                    },
                )
            )

        if item.available_volume_liters is None:
            reasons.append(make_reason("AVAILABLE_VOLUME_NOT_INFORMED", severity=ReasonSeverity.WARNING))
        elif scenario.requested_volume_liters > item.available_volume_liters:
            reasons.append(
                make_reason(
                    "AVAILABLE_VOLUME_INSUFFICIENT",
                    severity=ReasonSeverity.BLOCKING,
                    metadata={
                        "requested_volume_liters": str(scenario.requested_volume_liters),
                        "available_volume_liters": str(item.available_volume_liters),
                    },
                )
            )
        elif item.available_volume_liters > 0:
            margin = (item.available_volume_liters - scenario.requested_volume_liters) / item.available_volume_liters
            if margin <= self.LOW_MARGIN_RATIO:
                reasons.append(
                    make_reason(
                        "LOW_AVAILABLE_MARGIN",
                        severity=ReasonSeverity.WARNING,
                        metadata={
                            "requested_volume_liters": str(scenario.requested_volume_liters),
                            "available_volume_liters": str(item.available_volume_liters),
                        },
                    )
                )

        if scenario.required_delivery_at is not None:
            if item.delivery_expected_at is None:
                reasons.append(make_reason("DELIVERY_DATE_NOT_INFORMED", severity=ReasonSeverity.WARNING))
            elif item.delivery_expected_at > scenario.required_delivery_at:
                reasons.append(
                    make_reason(
                        "DELIVERY_AFTER_REQUIRED_DATE",
                        severity=ReasonSeverity.BLOCKING,
                        metadata={
                            "required_delivery_at": scenario.required_delivery_at.isoformat(),
                            "delivery_expected_at": item.delivery_expected_at.isoformat(),
                        },
                    )
                )

        if not item.payment_term_id:
            reasons.append(make_reason("MISSING_PAYMENT_TERM", severity=ReasonSeverity.BLOCKING))

        if scenario.ranking_mode == RankingMode.FINANCIAL_EQUIVALENT:
            if financial_parameter is None:
                reasons.append(make_reason("MISSING_FINANCIAL_PARAMETER", severity=ReasonSeverity.BLOCKING))
            elif financial_parameter.annual_effective_rate < 0 or financial_parameter.day_count_basis <= 0:
                reasons.append(make_reason("INVALID_FINANCIAL_PARAMETER", severity=ReasonSeverity.BLOCKING))

        if item.quoted_price_per_liter <= 0:
            reasons.append(make_reason("INVALID_DELIVERED_COST", severity=ReasonSeverity.BLOCKING))
        elif delivered_cost_per_liter is not None and delivered_cost_per_liter <= 0:
            reasons.append(make_reason("INVALID_DELIVERED_COST", severity=ReasonSeverity.BLOCKING))

        effective_valid_until = self.candidate_service.item_effective_valid_until(item, quote)
        if effective_valid_until - comp <= self.NEAR_EXPIRATION_WINDOW:
            reasons.append(
                make_reason(
                    "QUOTE_NEAR_EXPIRATION",
                    severity=ReasonSeverity.WARNING,
                    metadata={"effective_valid_until": effective_valid_until.isoformat()},
                )
            )

        return resolve_eligibility_status(reasons), reasons

    @staticmethod
    def financial_days_from_snapshot(payment_type_snapshot: str, payment_term_days_snapshot: int) -> int:
        try:
            payment_type = PaymentType(payment_type_snapshot)
        except ValueError:
            return max(payment_term_days_snapshot, 0)
        if payment_type in {PaymentType.CASH, PaymentType.ANTICIPATED}:
            return 0
        return max(payment_term_days_snapshot, 0)
