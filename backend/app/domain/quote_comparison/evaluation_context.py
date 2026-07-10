from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.models.financial_parameter import FinancialParameter
from app.services.quote_candidate_service import QuoteCandidate
from app.services.quote_cost_calculation_service import CostBreakdown
from app.services.quote_eligibility_service import ComparisonScenario
from app.services.quote_ranking_service import ProcessedOffer
from app.services.supplier_rule_service import EffectiveRuleResult


@dataclass
class CandidateEvaluationContext:
    """Contexto imutável de avaliação por candidato — resolvido uma única vez."""

    candidate: QuoteCandidate
    rule: EffectiveRuleResult
    costs: CostBreakdown
    eligibility_status: str
    eligibility_reasons: list[dict[str, Any]]
    effective_valid_until: datetime
    rule_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_processed_offer(
        self,
        *,
        ranking_mode: str,
        ranking_cost_per_liter: Decimal | None,
    ) -> ProcessedOffer:
        return ProcessedOffer(
            quote_id=self.candidate.quote.id,
            quote_item_id=self.candidate.item.id,
            distributor_id=self.candidate.quote.distributor_id,
            eligibility_status=self.eligibility_status,
            raw_price_per_liter=self.costs.raw_price_per_liter,
            delivered_cost_per_liter=self.costs.delivered_cost_per_liter,
            financial_equivalent_cost_per_liter=self.costs.financial_equivalent_cost_per_liter,
            ranking_cost_per_liter=ranking_cost_per_liter,
            distributor_name=self.candidate.distributor_name,
            delivery_expected_at=self.candidate.item.delivery_expected_at,
            effective_valid_until=self.effective_valid_until,
            activated_at=self.candidate.quote.activated_at,
        )

    def build_input_snapshot(self) -> dict[str, Any]:
        item = self.candidate.item
        quote = self.candidate.quote
        return {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "quote_item_id": str(item.id),
            "distributor_id": str(quote.distributor_id),
            "distributor_name": self.candidate.distributor_name,
            "distribution_base_id": str(item.distribution_base_id or quote.distribution_base_id)
            if (item.distribution_base_id or quote.distribution_base_id)
            else None,
            "payment_term_id": str(item.payment_term_id) if item.payment_term_id else None,
            "payment_term_name_snapshot": item.payment_term_name_snapshot,
            "payment_type_snapshot": item.payment_type_snapshot,
            "payment_term_days_snapshot": item.payment_term_days_snapshot,
            "quoted_price_per_liter": str(item.quoted_price_per_liter),
            "minimum_volume_liters": str(item.minimum_volume_liters) if item.minimum_volume_liters else None,
            "available_volume_liters": str(item.available_volume_liters) if item.available_volume_liters else None,
            "freight_calculation_type": item.freight_calculation_type,
            "activated_at": quote.activated_at.isoformat() if quote.activated_at else None,
            "effective_valid_until": self.effective_valid_until.isoformat(),
            "rule": self.rule_snapshot,
        }

    @staticmethod
    def rule_to_snapshot(rule: EffectiveRuleResult) -> dict[str, Any]:
        return {
            "rule_id": str(rule.rule_id) if rule.rule_id else None,
            "rule_source": rule.rule_source,
            "allowed": rule.allowed,
            "minimum_volume_liters": str(rule.minimum_volume_liters),
            "distribution_base_id": str(rule.distribution_base_id) if rule.distribution_base_id else None,
            "valid_from": rule.valid_from.isoformat() if rule.valid_from else None,
            "valid_until": rule.valid_until.isoformat() if rule.valid_until else None,
            "reason": rule.reason,
        }


@dataclass
class EvaluationBatch:
    """Lote de avaliação com dados capturados no início da execução."""

    scenario: ComparisonScenario
    financial_parameter: FinancialParameter | None
    financial_parameter_snapshot: dict[str, Any] | None
    contexts: list[CandidateEvaluationContext]
