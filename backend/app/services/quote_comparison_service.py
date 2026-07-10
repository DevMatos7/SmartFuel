from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.core.quote_comparison_enums import (
    ComparisonRunStatus,
    EligibilityStatus,
    METHODOLOGY_VERSION,
    RankingMode,
    RankingScope,
)
from app.domain.quote_comparison.evaluation_context import CandidateEvaluationContext
from app.domain.quote_comparison.snapshot_canonical import compute_snapshot_hash
from app.models.distributor import Distributor
from app.models.product import Product
from app.models.quote_comparison_run import QuoteComparisonResult, QuoteComparisonRun
from app.models.station import Station
from app.services.financial_parameter_service import FinancialParameterService
from app.services.quote_evaluation_service import QuoteEvaluationService
from app.services.quote_eligibility_service import ComparisonScenario
from app.services.quote_ranking_service import ProcessedOffer, QuoteRankingService
from app.services.quote_spread_service import QuoteSpreadService

logger = logging.getLogger(__name__)

METHODOLOGY_DOC = {
    "version": METHODOLOGY_VERSION,
    "ranking_modes": {
        "RAW": "Preço bruto por litro cotado.",
        "DELIVERED": "Preço cotado menos descontos e bonificações, mais frete e outros custos por litro.",
        "FINANCIAL_EQUIVALENT": "Custo entregue trazido a valor presente equivalente à vista.",
    },
    "formulas": {
        "freight_per_liter_total": "freight_value_total / requested_volume_liters",
        "delivered_cost_per_liter": "quoted_price - discount - rebate + freight + other_cost",
        "daily_rate": "(1 + annual_effective_rate) ^ (1/day_count_basis) - 1",
        "financial_equivalent_cost_per_liter": "delivered_cost / (1 + daily_rate) ^ financial_days",
        "spread_absolute": "highest_eligible_cost - lowest_eligible_cost",
        "spread_percent": "spread_absolute / lowest_eligible_cost * 100",
    },
    "rounding": "ROUND_HALF_UP; 8 casas por litro na persistência; 2 casas em totais.",
    "validity_rule": "comparison_datetime < effective_valid_until (vencido no instante exato de valid_until).",
    "historical_resolution": (
        "Regras e taxas são resolvidas pela vigência em comparison_datetime, "
        "não pelo estado administrativo active atual."
    ),
}


class QuoteComparisonService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.evaluation_service = QuoteEvaluationService(db)
        self.ranking_service = QuoteRankingService()
        self.spread_service = QuoteSpreadService()
        self.financial_service = FinancialParameterService(db)

    def _validate_scenario(
        self,
        *,
        requested_volume_liters: Decimal,
        comparison_datetime: datetime,
        required_delivery_at: datetime | None,
        ranking_mode: str,
        ranking_scope: str,
    ) -> None:
        if requested_volume_liters <= 0:
            raise AppError(
                "O volume solicitado deve ser maior que zero.",
                status_code=400,
                code="INVALID_REQUESTED_VOLUME",
            )
        now = datetime.now(UTC)
        comp = comparison_datetime if comparison_datetime.tzinfo else comparison_datetime.replace(tzinfo=UTC)
        if comp > now:
            raise AppError(
                "A data da comparação não pode estar no futuro.",
                status_code=400,
                code="COMPARISON_DATETIME_IN_FUTURE",
            )
        if required_delivery_at is not None:
            req = required_delivery_at if required_delivery_at.tzinfo else required_delivery_at.replace(tzinfo=UTC)
            if req < comp:
                raise AppError(
                    "A data limite de entrega deve ser posterior à comparação.",
                    status_code=400,
                    code="INVALID_COMPARISON_SCENARIO",
                )
        try:
            RankingMode(ranking_mode)
            RankingScope(ranking_scope)
        except ValueError as exc:
            raise AppError(
                "Revise os dados informados para a comparação.",
                status_code=400,
                code="INVALID_COMPARISON_SCENARIO",
            ) from exc

    def _build_hash_payload(
        self,
        *,
        run: QuoteComparisonRun,
        contexts: list[CandidateEvaluationContext],
        ranked: list[ProcessedOffer],
    ) -> dict:
        offer_by_item = {offer.quote_item_id: offer for offer in ranked}
        results_payload = []
        for ctx in sorted(contexts, key=lambda item: str(item.candidate.item.id)):
            offer = offer_by_item[ctx.candidate.item.id]
            results_payload.append(
                {
                    "quote_item_id": str(ctx.candidate.item.id),
                    "eligibility_status": ctx.eligibility_status,
                    "eligibility_reasons": ctx.eligibility_reasons,
                    "costs": {
                        "raw_price_per_liter": ctx.costs.raw_price_per_liter,
                        "delivered_cost_per_liter": ctx.costs.delivered_cost_per_liter,
                        "financial_equivalent_cost_per_liter": ctx.costs.financial_equivalent_cost_per_liter,
                    },
                    "rank_position": offer.rank_position,
                    "ranking_cost_per_liter": offer.ranking_cost_per_liter,
                    "input_snapshot": ctx.build_input_snapshot(),
                    "calculation_snapshot": ctx.costs.calculation_snapshot,
                }
            )
        return {
            "methodology_version": run.methodology_version,
            "input": run.input_snapshot,
            "summary": run.summary_snapshot,
            "results": results_payload,
        }

    async def run_comparison(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        product_id: uuid.UUID,
        requested_volume_liters: Decimal,
        comparison_datetime: datetime,
        required_delivery_at: datetime | None,
        ranking_mode: str,
        ranking_scope: str,
        created_by: uuid.UUID,
        reprocessed_from_run_id: uuid.UUID | None = None,
    ) -> QuoteComparisonRun:
        started = perf_counter()
        self._validate_scenario(
            requested_volume_liters=requested_volume_liters,
            comparison_datetime=comparison_datetime,
            required_delivery_at=required_delivery_at,
            ranking_mode=ranking_mode,
            ranking_scope=ranking_scope,
        )

        station = await self.db.get(Station, station_id)
        product = await self.db.get(Product, product_id)
        if station is None or station.organization_id != organization_id:
            raise AppError("Posto não encontrado.", status_code=404, code="NOT_FOUND")
        if product is None or product.organization_id != organization_id:
            raise AppError("Produto não encontrado.", status_code=404, code="NOT_FOUND")

        financial_parameter = await self.financial_service.find_effective(
            organization_id=organization_id,
            reference_datetime=comparison_datetime,
            historical=True,
        )

        scenario = ComparisonScenario(
            organization_id=organization_id,
            station_id=station_id,
            product_id=product_id,
            requested_volume_liters=requested_volume_liters,
            comparison_datetime=comparison_datetime,
            required_delivery_at=required_delivery_at,
            ranking_mode=ranking_mode,
        )

        run = QuoteComparisonRun(
            organization_id=organization_id,
            station_id=station_id,
            product_id=product_id,
            requested_volume_liters=requested_volume_liters,
            comparison_datetime=comparison_datetime,
            required_delivery_at=required_delivery_at,
            ranking_mode=ranking_mode,
            ranking_scope=ranking_scope,
            financial_parameter_id=financial_parameter.id if financial_parameter else None,
            methodology_version=METHODOLOGY_VERSION,
            status=ComparisonRunStatus.PROCESSING,
            reprocessed_from_run_id=reprocessed_from_run_id,
            created_by=created_by,
            created_at=datetime.now(UTC),
            input_snapshot={
                "scenario": {
                    "station_id": str(station_id),
                    "product_id": str(product_id),
                    "requested_volume_liters": str(requested_volume_liters),
                    "comparison_datetime": comparison_datetime.isoformat(),
                    "required_delivery_at": required_delivery_at.isoformat() if required_delivery_at else None,
                    "ranking_mode": ranking_mode,
                    "ranking_scope": ranking_scope,
                },
                "financial_parameter": QuoteEvaluationService.financial_parameter_snapshot(financial_parameter),
                "methodology_version": METHODOLOGY_VERSION,
            },
            summary_snapshot={},
        )
        self.db.add(run)
        await self.db.flush()

        try:
            batch = await self.evaluation_service.evaluate_batch(
                organization_id=organization_id,
                scenario=scenario,
                financial_parameter=financial_parameter,
            )
            run.input_snapshot["financial_parameter"] = batch.financial_parameter_snapshot

            processed: list[ProcessedOffer] = []
            for ctx in batch.contexts:
                ranking_cost = self.ranking_service.ranking_cost(
                    ranking_mode=ranking_mode,
                    raw_price=ctx.costs.raw_price_per_liter,
                    delivered_cost=ctx.costs.delivered_cost_per_liter,
                    financial_equivalent=ctx.costs.financial_equivalent_cost_per_liter,
                )
                if ctx.eligibility_status == EligibilityStatus.INELIGIBLE:
                    ranking_cost = None
                processed.append(ctx.to_processed_offer(ranking_mode=ranking_mode, ranking_cost_per_liter=ranking_cost))

            ranked = self.ranking_service.apply_ranking(
                processed,
                ranking_mode=ranking_mode,
                ranking_scope=ranking_scope,
                requested_volume_liters=requested_volume_liters,
            )
            summary = self.spread_service.compute(ranked)

            context_by_item = {ctx.candidate.item.id: ctx for ctx in batch.contexts}
            for offer in ranked:
                ctx = context_by_item[offer.quote_item_id]
                result = QuoteComparisonResult(
                    comparison_run_id=run.id,
                    quote_id=offer.quote_id,
                    quote_item_id=offer.quote_item_id,
                    distributor_id=offer.distributor_id,
                    distribution_base_id=ctx.candidate.item.distribution_base_id
                    or ctx.candidate.quote.distribution_base_id,
                    payment_term_id=ctx.candidate.item.payment_term_id,
                    eligibility_status=offer.eligibility_status,
                    eligibility_reasons=ctx.eligibility_reasons,
                    raw_price_per_liter=ctx.costs.raw_price_per_liter,
                    discount_per_liter=ctx.costs.discount_per_liter,
                    rebate_per_liter=ctx.costs.rebate_per_liter,
                    freight_per_liter=ctx.costs.freight_per_liter,
                    other_cost_per_liter=ctx.costs.other_cost_per_liter,
                    delivered_cost_per_liter=ctx.costs.delivered_cost_per_liter,
                    delivered_total=ctx.costs.delivered_total,
                    financial_days=ctx.costs.financial_days,
                    annual_effective_rate=ctx.costs.annual_effective_rate,
                    daily_rate=ctx.costs.daily_rate,
                    financial_equivalent_cost_per_liter=ctx.costs.financial_equivalent_cost_per_liter,
                    financial_equivalent_total=ctx.costs.financial_equivalent_total,
                    ranking_cost_per_liter=offer.ranking_cost_per_liter,
                    rank_position=offer.rank_position,
                    is_best_for_distributor=offer.is_best_for_distributor,
                    is_best_overall=offer.is_best_overall,
                    difference_per_liter=offer.difference_per_liter,
                    difference_total=offer.difference_total,
                    effective_valid_until=ctx.effective_valid_until,
                    delivery_expected_at=ctx.candidate.item.delivery_expected_at,
                    input_snapshot=ctx.build_input_snapshot(),
                    calculation_snapshot=ctx.costs.calculation_snapshot,
                    created_at=datetime.now(UTC),
                )
                self.db.add(result)

            run.eligible_count = summary.eligible_count
            run.warning_count = summary.warning_count
            run.ineligible_count = summary.ineligible_count
            run.distributor_count = summary.distributor_count
            run.best_cost_per_liter = summary.best_cost_per_liter
            run.highest_cost_per_liter = summary.highest_cost_per_liter
            run.average_cost_per_liter = summary.average_cost_per_liter
            run.spread_absolute = summary.spread_absolute
            run.spread_percent = summary.spread_percent
            run.summary_snapshot = {
                "eligible_count": summary.eligible_count,
                "warning_count": summary.warning_count,
                "ineligible_count": summary.ineligible_count,
                "distributor_count": summary.distributor_count,
                "best_cost_per_liter": str(summary.best_cost_per_liter) if summary.best_cost_per_liter else None,
                "highest_cost_per_liter": str(summary.highest_cost_per_liter)
                if summary.highest_cost_per_liter
                else None,
                "average_cost_per_liter": str(summary.average_cost_per_liter)
                if summary.average_cost_per_liter
                else None,
                "spread_absolute": str(summary.spread_absolute) if summary.spread_absolute else None,
                "spread_percent": str(summary.spread_percent) if summary.spread_percent else None,
                "candidate_count": len(batch.contexts),
                "ranking_scope": ranking_scope,
                "ranking_mode": ranking_mode,
            }
            run.status = ComparisonRunStatus.COMPLETED
            run.processing_duration_ms = int((perf_counter() - started) * 1000)
            run.calculation_hash = compute_snapshot_hash(
                self._build_hash_payload(run=run, contexts=batch.contexts, ranked=ranked)
            )
        except AppError:
            run.status = ComparisonRunStatus.FAILED
            run.processing_duration_ms = int((perf_counter() - started) * 1000)
            run.summary_snapshot = {"error": "Falha na validação da comparação."}
            await self.db.flush()
            raise
        except Exception as exc:
            logger.exception("Falha ao processar comparação %s", run.id)
            run.status = ComparisonRunStatus.FAILED
            run.processing_duration_ms = int((perf_counter() - started) * 1000)
            run.summary_snapshot = {"error": "Falha interna ao processar a comparação."}
            await self.db.flush()
            raise AppError(
                "Não foi possível concluir a comparação.",
                status_code=500,
                code="COMPARISON_PROCESSING_FAILED",
            ) from exc

        await self.db.flush()
        loaded = await self.db.execute(
            select(QuoteComparisonRun)
            .options(selectinload(QuoteComparisonRun.results))
            .where(QuoteComparisonRun.id == run.id)
        )
        return loaded.scalar_one()

    async def get_run(self, run_id: uuid.UUID, organization_id: uuid.UUID) -> QuoteComparisonRun:
        result = await self.db.execute(
            select(QuoteComparisonRun)
            .options(selectinload(QuoteComparisonRun.results))
            .where(QuoteComparisonRun.id == run_id, QuoteComparisonRun.organization_id == organization_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise AppError("Comparação não encontrada.", status_code=404, code="NOT_FOUND")
        return run

    async def list_runs(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        created_by: uuid.UUID | None = None,
        ranking_mode: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        allowed_station_ids: list[uuid.UUID] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QuoteComparisonRun], int]:
        query = select(QuoteComparisonRun).where(
            QuoteComparisonRun.organization_id == organization_id,
            QuoteComparisonRun.status == ComparisonRunStatus.COMPLETED,
        )
        if station_id:
            query = query.where(QuoteComparisonRun.station_id == station_id)
        if allowed_station_ids is not None:
            query = query.where(QuoteComparisonRun.station_id.in_(allowed_station_ids))
        if product_id:
            query = query.where(QuoteComparisonRun.product_id == product_id)
        if created_by:
            query = query.where(QuoteComparisonRun.created_by == created_by)
        if ranking_mode:
            query = query.where(QuoteComparisonRun.ranking_mode == ranking_mode)
        if date_from:
            query = query.where(QuoteComparisonRun.created_at >= date_from)
        if date_to:
            query = query.where(QuoteComparisonRun.created_at <= date_to)

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())
        query = (
            query.order_by(QuoteComparisonRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(query)).scalars().all()
        return list(rows), total

    async def reprocess(
        self,
        *,
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID,
        comparison_datetime: datetime | None = None,
        ranking_mode: str | None = None,
        ranking_scope: str | None = None,
        required_delivery_at: datetime | None = None,
        requested_volume_liters: Decimal | None = None,
    ) -> QuoteComparisonRun:
        original = await self.get_run(run_id, organization_id)
        if original.status != ComparisonRunStatus.COMPLETED:
            raise AppError(
                "A comparação ainda não foi concluída.",
                status_code=409,
                code="COMPARISON_NOT_COMPLETED",
            )
        return await self.run_comparison(
            organization_id=organization_id,
            station_id=original.station_id,
            product_id=original.product_id,
            requested_volume_liters=requested_volume_liters or original.requested_volume_liters,
            comparison_datetime=comparison_datetime or original.comparison_datetime,
            required_delivery_at=(
                required_delivery_at if required_delivery_at is not None else original.required_delivery_at
            ),
            ranking_mode=ranking_mode or original.ranking_mode,
            ranking_scope=ranking_scope or original.ranking_scope,
            created_by=created_by,
            reprocessed_from_run_id=original.id,
        )

    @staticmethod
    def methodology() -> dict:
        return METHODOLOGY_DOC

    async def build_distributor_map(self, run: QuoteComparisonRun) -> dict[uuid.UUID, Distributor]:
        distributor_ids = {result.distributor_id for result in run.results}
        if not distributor_ids:
            return {}
        rows = (
            await self.db.execute(select(Distributor).where(Distributor.id.in_(distributor_ids)))
        ).scalars().all()
        return {row.id: row for row in rows}

    @staticmethod
    def distributor_name_from_snapshot(result: QuoteComparisonResult) -> str | None:
        if isinstance(result.input_snapshot, dict):
            name = result.input_snapshot.get("distributor_name")
            if name:
                return str(name)
        return None
