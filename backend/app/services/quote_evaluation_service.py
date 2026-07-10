from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.quote_comparison.evaluation_context import (
    CandidateEvaluationContext,
    EvaluationBatch,
)
from app.models.financial_parameter import FinancialParameter
from app.services.quote_candidate_service import QuoteCandidate, QuoteCandidateService
from app.services.quote_cost_calculation_service import QuoteCostCalculationService
from app.services.quote_eligibility_service import ComparisonScenario, QuoteEligibilityService
from app.services.supplier_rule_service import EffectiveRuleResult, SupplierRuleService


class QuoteEvaluationService:
    """Avalia candidatos uma única vez, produzindo contexto imutável por oferta."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.candidate_service = QuoteCandidateService(db)
        self.eligibility_service = QuoteEligibilityService(self.candidate_service)
        self.cost_service = QuoteCostCalculationService(self.eligibility_service)
        self.supplier_rule_service = SupplierRuleService(db)

    @staticmethod
    def financial_parameter_snapshot(parameter: FinancialParameter | None) -> dict | None:
        if parameter is None:
            return None
        return {
            "id": str(parameter.id),
            "annual_effective_rate": str(parameter.annual_effective_rate),
            "day_count_basis": parameter.day_count_basis,
            "methodology_version": parameter.methodology_version,
            "valid_from": parameter.valid_from.isoformat(),
            "valid_until": parameter.valid_until.isoformat() if parameter.valid_until else None,
            "active": parameter.active,
        }

    async def _resolve_rule(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        candidate: QuoteCandidate,
        product_id: uuid.UUID,
        comparison_datetime,
    ) -> EffectiveRuleResult:
        base_id = candidate.item.distribution_base_id or candidate.quote.distribution_base_id
        return await self.supplier_rule_service.resolve_effective_rule(
            organization_id=organization_id,
            station_id=station_id,
            distributor_id=candidate.quote.distributor_id,
            product_id=product_id,
            reference_date=comparison_datetime.date(),
            distribution_base_id=base_id,
            historical=True,
        )

    async def evaluate_batch(
        self,
        *,
        organization_id: uuid.UUID,
        scenario: ComparisonScenario,
        financial_parameter: FinancialParameter | None,
    ) -> EvaluationBatch:
        candidates = await self.candidate_service.find_candidates(
            organization_id=organization_id,
            station_id=scenario.station_id,
            product_id=scenario.product_id,
            comparison_datetime=scenario.comparison_datetime,
        )

        contexts: list[CandidateEvaluationContext] = []
        for candidate in candidates:
            rule = await self._resolve_rule(
                organization_id=organization_id,
                station_id=scenario.station_id,
                candidate=candidate,
                product_id=scenario.product_id,
                comparison_datetime=scenario.comparison_datetime,
            )
            costs = self.cost_service.calculate(
                candidate,
                requested_volume_liters=scenario.requested_volume_liters,
                financial_parameter=financial_parameter,
            )
            eligibility_status, reasons = self.eligibility_service.evaluate(
                candidate,
                scenario=scenario,
                rule=rule,
                financial_parameter=financial_parameter,
                delivered_cost_per_liter=costs.delivered_cost_per_liter,
            )
            effective_valid_until = self.candidate_service.item_effective_valid_until(
                candidate.item, candidate.quote
            )
            contexts.append(
                CandidateEvaluationContext(
                    candidate=candidate,
                    rule=rule,
                    costs=costs,
                    eligibility_status=eligibility_status,
                    eligibility_reasons=[
                        {
                            "code": reason.code,
                            "severity": reason.severity,
                            "message": reason.message,
                            "metadata": reason.metadata,
                        }
                        for reason in reasons
                    ],
                    effective_valid_until=effective_valid_until,
                    rule_snapshot=CandidateEvaluationContext.rule_to_snapshot(rule),
                )
            )

        return EvaluationBatch(
            scenario=scenario,
            financial_parameter=financial_parameter,
            financial_parameter_snapshot=self.financial_parameter_snapshot(financial_parameter),
            contexts=contexts,
        )
