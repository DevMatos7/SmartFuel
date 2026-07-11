"""Orquestrador Compra real × melhor cotação — reutiliza motor Sprint 4."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.purchase_benchmark_enums import (
    BenchmarkComparisonMode,
    BenchmarkDecisionResult,
    BenchmarkItemStatus,
    BenchmarkOverrideType,
    BenchmarkRunStatus,
    BenchmarkTriggerType,
    FinancialComparisonStatus,
    PurchaseReferenceConfidence,
)
from app.core.quote_comparison_enums import EligibilityStatus, RankingMode, RankingScope
from app.domain.quote_comparison.snapshot_canonical import compute_snapshot_hash
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.purchase_benchmarks import (
    PurchaseBenchmarkOverride,
    PurchaseBenchmarkParameter,
    PurchaseQuoteBenchmarkCandidate,
    PurchaseQuoteBenchmarkItem,
    PurchaseQuoteBenchmarkRun,
)
from app.services.financial_parameter_service import FinancialParameterService
from app.services.purchase_benchmark_support import (
    ActualPurchaseCostService,
    PurchaseBenchmarkReferenceService,
    PurchaseItemGroupingService,
    PurchaseProductGroup,
    ReferenceResolution,
)
from app.services.quote_eligibility_service import ComparisonScenario
from app.services.quote_evaluation_service import QuoteEvaluationService
from app.services.quote_ranking_service import QuoteRankingService

_ZERO = Decimal("0")


class PurchaseQuoteBenchmarkService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.reference_service = PurchaseBenchmarkReferenceService(db)
        self.grouping_service = PurchaseItemGroupingService()
        self.cost_service = ActualPurchaseCostService()
        self.evaluation_service = QuoteEvaluationService(db)
        self.ranking_service = QuoteRankingService()
        self.financial_service = FinancialParameterService(db)

    async def run_for_invoice(
        self,
        *,
        organization_id: uuid.UUID,
        invoice_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        requested_by: uuid.UUID | None,
        comparison_mode: str | None = None,
        trigger_type: str = BenchmarkTriggerType.MANUAL,
        reprocess_of_run_id: uuid.UUID | None = None,
        reprocess_reason: str | None = None,
    ) -> PurchaseQuoteBenchmarkRun:
        invoice = await self._load_invoice(organization_id, invoice_id, station_ids)
        if invoice is None:
            raise ValueError("NOT_FOUND")

        exclude = await self._has_exclude_override(organization_id, invoice.id)
        now = datetime.now(UTC)
        reference = await self.reference_service.resolve(
            invoice=invoice, organization_id=organization_id
        )
        # Tolerância/parâmetros versionados no instante de referência T (não “agora”).
        params = await self._resolve_parameters(
            organization_id, reference.reference_datetime or now
        )
        mode = comparison_mode or (
            params.default_comparison_mode if params else BenchmarkComparisonMode.DELIVERED_COST
        )
        if mode not in {m.value for m in BenchmarkComparisonMode}:
            mode = BenchmarkComparisonMode.DELIVERED_COST

        items = await self._load_items(invoice.id)
        groups = self.grouping_service.group(items)
        actual_distributor_id = await self._resolve_actual_distributor(
            organization_id, invoice
        )

        run = PurchaseQuoteBenchmarkRun(
            id=uuid.uuid4(),
            organization_id=organization_id,
            purchase_invoice_id=invoice.id,
            station_id=invoice.station_id,
            status=BenchmarkRunStatus.PROCESSING,
            comparison_mode=mode,
            reference_datetime=reference.reference_datetime,
            reference_source=reference.source,
            reference_confidence=reference.confidence,
            trigger_type=trigger_type,
            requested_by=requested_by,
            reprocess_of_run_id=reprocess_of_run_id,
            reprocess_reason=reprocess_reason,
            input_snapshot={
                "invoice_id": str(invoice.id),
                "source_document_number": invoice.source_document_number,
                "station_id": str(invoice.station_id),
                "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
                "entry_date": invoice.entry_date.isoformat() if invoice.entry_date else None,
                "distributor_id": str(invoice.distributor_id) if invoice.distributor_id else None,
                "reference": {
                    "datetime": reference.reference_datetime.isoformat()
                    if reference.reference_datetime
                    else None,
                    "source": reference.source,
                    "confidence": reference.confidence,
                    "warnings": reference.warnings,
                },
                "comparison_mode": mode,
                "excluded": exclude,
                "group_count": len(groups),
            },
            item_count=len(groups),
            actual_total_cost=_ZERO,
            started_at=now,
            created_at=now,
        )
        self.db.add(run)
        await self.db.flush()

        if exclude:
            run.status = BenchmarkRunStatus.COMPLETED
            run.finished_at = datetime.now(UTC)
            run.output_snapshot = {"excluded": True, "reason": "EXCLUDE_BENCHMARK override"}
            run.snapshot_hash = compute_snapshot_hash(
                {"input": run.input_snapshot, "output": run.output_snapshot}
            )
            await self.db.flush()
            return run

        ranking_mode = (
            RankingMode.FINANCIAL_EQUIVALENT
            if mode == BenchmarkComparisonMode.FINANCIAL_EQUIVALENT
            else RankingMode.DELIVERED
        )

        financial_param = None
        financial_status = FinancialComparisonStatus.UNAVAILABLE
        if reference.reference_datetime is not None:
            financial_param = await self.financial_service.find_effective(
                organization_id=organization_id,
                reference_datetime=reference.reference_datetime,
                historical=True,
            )
            if mode == BenchmarkComparisonMode.FINANCIAL_EQUIVALENT and financial_param is not None:
                financial_status = FinancialComparisonStatus.AVAILABLE

        warning_count = 0
        error_count = 0
        benchmarked = 0
        actual_total = _ZERO
        benchmark_total = _ZERO
        variance_total = _ZERO
        opportunity_total = _ZERO
        advantage_total = _ZERO
        item_outputs: list[dict] = []

        for group in groups:
            item_row, item_out, warns, errs = await self._benchmark_group(
                run=run,
                invoice=invoice,
                group=group,
                reference=reference,
                actual_distributor_id=actual_distributor_id,
                ranking_mode=ranking_mode,
                comparison_mode=mode,
                financial_param=financial_param,
                financial_status=financial_status,
                params=params,
                allow_low_confidence=bool(params.allow_low_confidence_reference if params else True),
            )
            self.db.add(item_row)
            await self.db.flush()
            warning_count += warns
            error_count += errs
            if item_row.benchmark_status in {
                BenchmarkItemStatus.BENCHMARKED,
                BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS,
            }:
                benchmarked += 1
            actual_total += item_row.actual_delivered_cost or _ZERO
            if item_row.benchmark_total_cost is not None:
                benchmark_total += item_row.benchmark_total_cost
            if item_row.cost_variance_amount is not None:
                variance_total += item_row.cost_variance_amount
            if item_row.opportunity_amount is not None:
                opportunity_total += item_row.opportunity_amount
            if item_row.actual_advantage_amount is not None:
                advantage_total += item_row.actual_advantage_amount
            item_outputs.append(item_out)

        run.item_count = len(groups)
        run.benchmarked_item_count = benchmarked
        run.warning_count = warning_count
        run.error_count = error_count
        run.actual_total_cost = actual_total
        run.benchmark_total_cost = benchmark_total if benchmarked else None
        run.cost_variance_amount = variance_total if benchmarked else None
        run.opportunity_amount = opportunity_total if benchmarked else None
        run.actual_advantage_amount = advantage_total if benchmarked else None
        run.finished_at = datetime.now(UTC)

        if error_count and not benchmarked:
            run.status = BenchmarkRunStatus.FAILED
        elif benchmarked and (warning_count or error_count or benchmarked < len(groups)):
            run.status = (
                BenchmarkRunStatus.PARTIAL
                if benchmarked < len(groups)
                else BenchmarkRunStatus.COMPLETED_WITH_WARNINGS
            )
        else:
            run.status = BenchmarkRunStatus.COMPLETED

        run.output_snapshot = {
            "items": item_outputs,
            "financial_comparison_status": financial_status,
            "parameters": self._params_snapshot(params),
            "totals": {
                "actual_total_cost": str(actual_total),
                "benchmark_total_cost": str(benchmark_total) if benchmarked else None,
                "cost_variance_amount": str(variance_total) if benchmarked else None,
                "opportunity_amount": str(opportunity_total) if benchmarked else None,
                "actual_advantage_amount": str(advantage_total) if benchmarked else None,
            },
        }
        run.snapshot_hash = compute_snapshot_hash(
            {"input": run.input_snapshot, "output": run.output_snapshot}
        )
        await self.db.flush()
        return run

    async def reprocess(
        self,
        *,
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        requested_by: uuid.UUID | None,
        reason: str,
    ) -> PurchaseQuoteBenchmarkRun:
        previous = (
            await self.db.execute(
                select(PurchaseQuoteBenchmarkRun).where(
                    PurchaseQuoteBenchmarkRun.id == run_id,
                    PurchaseQuoteBenchmarkRun.organization_id == organization_id,
                    PurchaseQuoteBenchmarkRun.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()
        if previous is None:
            raise ValueError("NOT_FOUND")
        return await self.run_for_invoice(
            organization_id=organization_id,
            invoice_id=previous.purchase_invoice_id,
            station_ids=station_ids,
            requested_by=requested_by,
            comparison_mode=previous.comparison_mode,
            trigger_type=BenchmarkTriggerType.REPROCESS,
            reprocess_of_run_id=previous.id,
            reprocess_reason=reason,
        )

    async def _benchmark_group(
        self,
        *,
        run: PurchaseQuoteBenchmarkRun,
        invoice: FuelPurchaseInvoice,
        group: PurchaseProductGroup,
        reference: ReferenceResolution,
        actual_distributor_id: uuid.UUID | None,
        ranking_mode: str,
        comparison_mode: str,
        financial_param,
        financial_status: str,
        params: PurchaseBenchmarkParameter | None,
        allow_low_confidence: bool,
    ) -> tuple[PurchaseQuoteBenchmarkItem, dict, int, int]:
        now = datetime.now(UTC)
        warnings: list[dict] = []
        exclusion: list[dict] = []
        warns = 0
        errs = 0

        status = BenchmarkItemStatus.BENCHMARKED
        decision = BenchmarkDecisionResult.NOT_COMPARABLE
        per_liter = self.cost_service.cost_per_liter(
            total_cost=group.commercial_delivered_cost, volume_liters=group.volume_liters
        )

        if group.unmapped:
            status = BenchmarkItemStatus.UNMAPPED_PRODUCT
            exclusion.append({"code": "UNMAPPED_PRODUCT"})
            errs += 1
        elif group.volume_liters is None or group.volume_liters <= 0:
            status = BenchmarkItemStatus.MISSING_VOLUME
            exclusion.append({"code": "MISSING_VOLUME"})
            errs += 1
        elif per_liter is None:
            status = BenchmarkItemStatus.MISSING_ACTUAL_COST
            exclusion.append({"code": "MISSING_ACTUAL_COST"})
            errs += 1
        elif reference.reference_datetime is None:
            status = BenchmarkItemStatus.REFERENCE_TIME_UNAVAILABLE
            exclusion.append({"code": "REFERENCE_TIME_UNAVAILABLE"})
            errs += 1
        elif (
            reference.confidence == PurchaseReferenceConfidence.LOW
            and not allow_low_confidence
        ):
            status = BenchmarkItemStatus.NOT_COMPARABLE
            exclusion.append({"code": "LOW_CONFIDENCE_REFERENCE_BLOCKED"})
            errs += 1
        elif (
            comparison_mode == BenchmarkComparisonMode.FINANCIAL_EQUIVALENT
            and financial_status != FinancialComparisonStatus.AVAILABLE
        ):
            status = BenchmarkItemStatus.NOT_COMPARABLE
            exclusion.append({"code": "FINANCIAL_COMPARISON_UNAVAILABLE"})
            warnings.append({"code": "financial_comparison_status", "value": financial_status})
            warns += 1

        if actual_distributor_id is None:
            warnings.append({"code": BenchmarkItemStatus.UNMAPPED_ACTUAL_SUPPLIER})
            warns += 1
        for w in reference.warnings:
            warnings.append({"code": "REFERENCE_WARNING", "message": w})
            warns += 1

        item = PurchaseQuoteBenchmarkItem(
            id=uuid.uuid4(),
            benchmark_run_id=run.id,
            organization_id=run.organization_id,
            station_id=run.station_id,
            purchase_invoice_id=invoice.id,
            group_key=group.group_key,
            canonical_product_id=group.canonical_product_id,
            actual_distributor_id=actual_distributor_id,
            volume_liters=group.volume_liters,
            actual_delivered_cost=group.commercial_delivered_cost,
            actual_delivered_cost_per_liter=per_liter,
            benchmark_status=status,
            decision_result=decision,
            candidate_count=0,
            eligible_candidate_count=0,
            exclusion_reasons=exclusion or None,
            warnings=warnings or None,
            input_snapshot={
                "group_key": group.group_key,
                "item_ids": [str(i) for i in group.item_ids],
                "volume_liters": str(group.volume_liters),
                "commercial_delivered_cost": str(group.commercial_delivered_cost),
                "actual_cost_per_liter": str(per_liter) if per_liter is not None else None,
                "source_product_ids": group.source_product_ids,
            },
            created_at=now,
        )

        if status not in {
            BenchmarkItemStatus.BENCHMARKED,
            BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS,
        } and status != BenchmarkItemStatus.BENCHMARKED:
            # early exit for non-comparable (unless only warnings pending after ranking)
            if status != BenchmarkItemStatus.BENCHMARKED:
                item.decision_result = BenchmarkDecisionResult.NOT_COMPARABLE
                if status == BenchmarkItemStatus.UNMAPPED_ACTUAL_SUPPLIER:
                    pass
                item.result_snapshot = {"status": status}
                item.snapshot_hash = compute_snapshot_hash(
                    {"input": item.input_snapshot, "result": item.result_snapshot}
                )
                # If we already failed hard, return
                if status not in {BenchmarkItemStatus.BENCHMARKED, BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS}:
                    # Allow continuing only when we intended to rank — here we stop
                    if exclusion:
                        out = {"group_key": group.group_key, "status": status, "decision": decision}
                        return item, out, warns, errs

        # Rank only when comparable core fields exist
        can_rank = (
            group.canonical_product_id is not None
            and group.volume_liters > 0
            and per_liter is not None
            and reference.reference_datetime is not None
            and not (
                comparison_mode == BenchmarkComparisonMode.FINANCIAL_EQUIVALENT
                and financial_status != FinancialComparisonStatus.AVAILABLE
            )
            and not (
                reference.confidence == PurchaseReferenceConfidence.LOW and not allow_low_confidence
            )
        )
        if not can_rank:
            item.decision_result = BenchmarkDecisionResult.NOT_COMPARABLE
            item.result_snapshot = {"status": item.benchmark_status, "decision": item.decision_result}
            item.snapshot_hash = compute_snapshot_hash(
                {"input": item.input_snapshot, "result": item.result_snapshot}
            )
            out = {
                "group_key": group.group_key,
                "status": item.benchmark_status,
                "decision": item.decision_result,
            }
            return item, out, warns, errs

        scenario = ComparisonScenario(
            organization_id=run.organization_id,
            station_id=run.station_id,
            product_id=group.canonical_product_id,  # type: ignore[arg-type]
            requested_volume_liters=group.volume_liters,
            comparison_datetime=reference.reference_datetime,  # type: ignore[arg-type]
            required_delivery_at=None,
            ranking_mode=ranking_mode,
        )
        batch = await self.evaluation_service.evaluate_batch(
            organization_id=run.organization_id,
            scenario=scenario,
            financial_parameter=financial_param,
        )
        offers = []
        for ctx in batch.contexts:
            ranking_cost = self.ranking_service.ranking_cost(
                ranking_mode=ranking_mode,
                raw_price=ctx.costs.raw_price_per_liter,
                delivered_cost=ctx.costs.delivered_cost_per_liter,
                financial_equivalent=ctx.costs.financial_equivalent_cost_per_liter,
            )
            offer = ctx.to_processed_offer(
                ranking_mode=ranking_mode, ranking_cost_per_liter=ranking_cost
            )
            offers.append(offer)

        ranked = self.ranking_service.apply_ranking(
            offers,
            ranking_mode=ranking_mode,
            ranking_scope=RankingScope.ALL_OFFERS,
            requested_volume_liters=group.volume_liters,
        )
        item.candidate_count = len(ranked)
        eligible = [
            o
            for o in ranked
            if o.eligibility_status
            in {EligibilityStatus.ELIGIBLE, EligibilityStatus.ELIGIBLE_WITH_WARNINGS}
            and o.rank_position is not None
        ]
        item.eligible_candidate_count = len(eligible)

        self.db.add(item)
        await self.db.flush()

        # Persist candidates
        for offer in ranked:
            blocking = None
            warn_payload = None
            # find matching context for reasons
            ctx = next(
                (c for c in batch.contexts if c.candidate.item.id == offer.quote_item_id),
                None,
            )
            if ctx is not None:
                blocking = [
                    r for r in ctx.eligibility_reasons if r.get("severity") in {"BLOCKING", "ERROR", "blocking"}
                ] or ctx.eligibility_reasons
                warn_payload = [
                    r for r in ctx.eligibility_reasons if str(r.get("severity", "")).upper() == "WARNING"
                ] or None
            cand = PurchaseQuoteBenchmarkCandidate(
                id=uuid.uuid4(),
                benchmark_item_id=item.id,
                quote_id=offer.quote_id,
                quote_item_id=offer.quote_item_id,
                distributor_id=offer.distributor_id,
                eligibility_status=offer.eligibility_status,
                blocking_reasons=blocking,
                warnings=warn_payload,
                raw_price_per_liter=offer.raw_price_per_liter,
                delivered_cost_per_liter=offer.delivered_cost_per_liter,
                financial_equivalent_per_liter=offer.financial_equivalent_cost_per_liter,
                ranking_position=offer.rank_position,
                is_best=bool(offer.is_best_overall),
                candidate_snapshot=ctx.build_input_snapshot() if ctx else None,
                created_at=now,
            )
            self.db.add(cand)

        if item.candidate_count == 0:
            item.benchmark_status = BenchmarkItemStatus.NO_QUOTES_AVAILABLE
            item.decision_result = BenchmarkDecisionResult.NO_BENCHMARK
            exclusion.append({"code": "NO_QUOTES_AVAILABLE"})
            item.exclusion_reasons = exclusion
            errs += 1
        elif item.eligible_candidate_count == 0:
            item.benchmark_status = BenchmarkItemStatus.NO_ELIGIBLE_QUOTES
            item.decision_result = BenchmarkDecisionResult.NO_BENCHMARK
            exclusion.append({"code": "NO_ELIGIBLE_QUOTES"})
            item.exclusion_reasons = exclusion
            errs += 1
        else:
            best = next((o for o in ranked if o.is_best_overall), eligible[0])
            bench_per_l = best.ranking_cost_per_liter or best.delivered_cost_per_liter
            item.best_quote_id = best.quote_id
            item.best_quote_item_id = best.quote_item_id
            item.best_distributor_id = best.distributor_id
            item.benchmark_cost_per_liter = bench_per_l
            item.benchmark_total_cost = (bench_per_l * group.volume_liters).quantize(Decimal("0.0001"))
            variance_pl = (per_liter - bench_per_l).quantize(Decimal("0.00000001"))  # type: ignore[operator]
            variance_amt = (variance_pl * group.volume_liters).quantize(Decimal("0.0001"))
            item.cost_variance_per_liter = variance_pl
            item.cost_variance_amount = variance_amt
            item.opportunity_amount = max(variance_amt, _ZERO)
            item.actual_advantage_amount = max(-variance_amt, _ZERO)

            if actual_distributor_id is not None:
                match = next(
                    (o for o in eligible if o.distributor_id == actual_distributor_id),
                    None,
                )
                item.actual_distributor_rank = match.rank_position if match else None
            else:
                # keep warning already added
                pass

            item.decision_result = self._decision_result(
                variance_pl=variance_pl,
                actual_per_l=per_liter,  # type: ignore[arg-type]
                params=params,
            )
            item.benchmark_status = (
                BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS
                if warns
                else BenchmarkItemStatus.BENCHMARKED
            )

        item.result_snapshot = {
            "status": item.benchmark_status,
            "decision": item.decision_result,
            "best_quote_id": str(item.best_quote_id) if item.best_quote_id else None,
            "benchmark_cost_per_liter": str(item.benchmark_cost_per_liter)
            if item.benchmark_cost_per_liter is not None
            else None,
            "cost_variance_per_liter": str(item.cost_variance_per_liter)
            if item.cost_variance_per_liter is not None
            else None,
            "opportunity_amount": str(item.opportunity_amount)
            if item.opportunity_amount is not None
            else None,
            "actual_advantage_amount": str(item.actual_advantage_amount)
            if item.actual_advantage_amount is not None
            else None,
            "actual_distributor_rank": item.actual_distributor_rank,
            "candidate_count": item.candidate_count,
            "eligible_candidate_count": item.eligible_candidate_count,
        }
        item.snapshot_hash = compute_snapshot_hash(
            {"input": item.input_snapshot, "result": item.result_snapshot}
        )
        out = {
            "group_key": group.group_key,
            "status": item.benchmark_status,
            "decision": item.decision_result,
            "variance_per_liter": str(item.cost_variance_per_liter)
            if item.cost_variance_per_liter is not None
            else None,
        }
        return item, out, warns, errs

    def _decision_result(
        self,
        *,
        variance_pl: Decimal,
        actual_per_l: Decimal,
        params: PurchaseBenchmarkParameter | None,
    ) -> str:
        abs_tol = params.absolute_tolerance_per_liter if params else _ZERO
        pct_tol = params.percentage_tolerance if params else _ZERO
        if variance_pl == 0:
            return BenchmarkDecisionResult.BEST_OR_TIED
        if variance_pl < 0:
            return BenchmarkDecisionResult.BELOW_BENCHMARK
        within_abs = abs(variance_pl) <= abs_tol
        within_pct = False
        if actual_per_l > 0 and pct_tol > 0:
            within_pct = abs(variance_pl / actual_per_l) <= pct_tol
        if within_abs or within_pct:
            return BenchmarkDecisionResult.WITHIN_TOLERANCE
        return BenchmarkDecisionResult.ABOVE_BEST

    async def _load_invoice(
        self,
        organization_id: uuid.UUID,
        invoice_id: uuid.UUID,
        station_ids: list[uuid.UUID],
    ) -> FuelPurchaseInvoice | None:
        return (
            await self.db.execute(
                select(FuelPurchaseInvoice).where(
                    FuelPurchaseInvoice.id == invoice_id,
                    FuelPurchaseInvoice.organization_id == organization_id,
                    FuelPurchaseInvoice.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()

    async def _load_items(self, invoice_id: uuid.UUID) -> list[FuelPurchaseItem]:
        return list(
            (
                await self.db.execute(
                    select(FuelPurchaseItem).where(FuelPurchaseItem.purchase_invoice_id == invoice_id)
                )
            ).scalars().all()
        )

    async def _resolve_actual_distributor(
        self, organization_id: uuid.UUID, invoice: FuelPurchaseInvoice
    ) -> uuid.UUID | None:
        overrides = (
            await self.db.execute(
                select(PurchaseBenchmarkOverride)
                .where(
                    PurchaseBenchmarkOverride.organization_id == organization_id,
                    PurchaseBenchmarkOverride.purchase_invoice_id == invoice.id,
                    PurchaseBenchmarkOverride.override_type == BenchmarkOverrideType.ACTUAL_DISTRIBUTOR,
                    PurchaseBenchmarkOverride.deactivated_at.is_(None),
                )
                .order_by(PurchaseBenchmarkOverride.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if overrides is not None:
            raw = (overrides.new_value or {}).get("distributor_id")
            if raw:
                return uuid.UUID(str(raw))
        return invoice.distributor_id

    async def _has_exclude_override(self, organization_id: uuid.UUID, invoice_id: uuid.UUID) -> bool:
        row = (
            await self.db.execute(
                select(PurchaseBenchmarkOverride.id)
                .where(
                    PurchaseBenchmarkOverride.organization_id == organization_id,
                    PurchaseBenchmarkOverride.purchase_invoice_id == invoice_id,
                    PurchaseBenchmarkOverride.override_type == BenchmarkOverrideType.EXCLUDE_BENCHMARK,
                    PurchaseBenchmarkOverride.deactivated_at.is_(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return row is not None

    async def _resolve_parameters(
        self, organization_id: uuid.UUID, reference: datetime
    ) -> PurchaseBenchmarkParameter | None:
        return (
            await self.db.execute(
                select(PurchaseBenchmarkParameter)
                .where(
                    PurchaseBenchmarkParameter.organization_id == organization_id,
                    PurchaseBenchmarkParameter.valid_from <= reference,
                    (
                        PurchaseBenchmarkParameter.valid_until.is_(None)
                        | (PurchaseBenchmarkParameter.valid_until > reference)
                    ),
                )
                .order_by(PurchaseBenchmarkParameter.valid_from.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    @staticmethod
    def _params_snapshot(params: PurchaseBenchmarkParameter | None) -> dict | None:
        if params is None:
            return None
        return {
            "id": str(params.id),
            "absolute_tolerance_per_liter": str(params.absolute_tolerance_per_liter),
            "percentage_tolerance": str(params.percentage_tolerance),
            "allow_low_confidence_reference": params.allow_low_confidence_reference,
            "default_comparison_mode": params.default_comparison_mode,
            "valid_from": params.valid_from.isoformat(),
            "valid_until": params.valid_until.isoformat() if params.valid_until else None,
        }
