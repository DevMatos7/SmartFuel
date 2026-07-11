"""Orquestrador Sprint 10 — análise de mercado (somente PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.market_analysis_enums import (
    AlignmentPolicy,
    AnalysisTriggerType,
    EventDirection,
    InternalSeriesType,
    MarketAnalysisStatus,
    MarketAnalysisType,
    MarketFrequency,
    MarketTransformation,
    MetricType,
    QualityStatus,
)
from app.domain.quote_comparison.snapshot_canonical import compute_snapshot_hash
from app.models.external_data import ExternalObservation, ExternalSeries
from app.models.market_analysis import (
    InternalMarketSeriesPoint,
    MarketAlignedObservation,
    MarketAnalysisParameter,
    MarketAnalysisResult,
    MarketAnalysisRun,
    MarketPassThroughEvent,
)
from app.services.audit_service import AuditContext, AuditService
from app.services.market_analysis.alignment import (
    SeriesPoint,
    align_series,
    apply_transformation,
)
from app.services.market_analysis.statistics import (
    pass_through_elasticity,
    pass_through_ratio,
    pearson,
    select_best_lag,
    spearman,
)

DISCLAIMER = (
    "Resultados exploratórios de associação observada. "
    "Correlação, defasagem e repasse não constituem prova de causalidade "
    "nem recomendação de compra ou precificação."
)


class MarketAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def get_or_create_parameters(
        self, organization_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> MarketAnalysisParameter:
        row = (
            await self.db.execute(
                select(MarketAnalysisParameter)
                .where(
                    MarketAnalysisParameter.organization_id == organization_id,
                    MarketAnalysisParameter.active.is_(True),
                )
                .order_by(MarketAnalysisParameter.valid_from.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row:
            return row
        row = MarketAnalysisParameter(
            organization_id=organization_id,
            valid_from=datetime.now(UTC),
            created_by=None,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def upsert_parameters(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
    ) -> MarketAnalysisParameter:
        current = await self.get_or_create_parameters(organization_id, user_id)
        current.active = False
        current.valid_until = datetime.now(UTC)
        new = MarketAnalysisParameter(
            organization_id=organization_id,
            minimum_sample_size=int(data.get("minimum_sample_size", current.minimum_sample_size)),
            maximum_missing_percentage=Decimal(
                str(data.get("maximum_missing_percentage", current.maximum_missing_percentage))
            ),
            maximum_carry_forward_age=int(
                data.get("maximum_carry_forward_age", current.maximum_carry_forward_age)
            ),
            minimum_lag=int(data.get("minimum_lag", current.minimum_lag)),
            maximum_lag=int(data.get("maximum_lag", current.maximum_lag)),
            lag_unit=data.get("lag_unit", current.lag_unit),
            minimum_reference_change=Decimal(
                str(data.get("minimum_reference_change", current.minimum_reference_change))
            ),
            default_frequency=data.get("default_frequency", current.default_frequency),
            default_transformation=data.get(
                "default_transformation", current.default_transformation
            ),
            valid_from=datetime.now(UTC),
            active=True,
            created_by=user_id,
        )
        self.db.add(new)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="market_analysis_parameters",
            entity_id=new.id,
            action="UPSERT",
            after_data={"minimum_sample_size": new.minimum_sample_size},
        )
        await self.db.commit()
        await self.db.refresh(new)
        return new

    async def upsert_internal_point(
        self,
        *,
        organization_id: uuid.UUID,
        series_type: str,
        observation_datetime: datetime,
        available_at: datetime,
        value: Decimal,
        unit: str,
        source_entity_type: str,
        source_entity_id: uuid.UUID | None = None,
        station_id: uuid.UUID | None = None,
        canonical_product_id: uuid.UUID | None = None,
        distributor_id: uuid.UUID | None = None,
        volume_weight: Decimal | None = None,
    ) -> InternalMarketSeriesPoint:
        payload = {
            "series_type": series_type,
            "observation_datetime": observation_datetime.isoformat(),
            "value": str(value),
            "station_id": str(station_id) if station_id else None,
            "product_id": str(canonical_product_id) if canonical_product_id else None,
            "distributor_id": str(distributor_id) if distributor_id else None,
        }
        digest = compute_snapshot_hash(payload)
        existing = (
            await self.db.execute(
                select(InternalMarketSeriesPoint).where(
                    InternalMarketSeriesPoint.organization_id == organization_id,
                    InternalMarketSeriesPoint.series_type == series_type,
                    InternalMarketSeriesPoint.observation_datetime == observation_datetime,
                    InternalMarketSeriesPoint.station_id == station_id,
                    InternalMarketSeriesPoint.canonical_product_id == canonical_product_id,
                    InternalMarketSeriesPoint.distributor_id == distributor_id,
                )
            )
        ).scalar_one_or_none()
        if existing and existing.source_record_hash == digest:
            return existing
        if existing:
            existing.value = value
            existing.available_at = available_at
            existing.source_record_hash = digest
            existing.volume_weight = volume_weight
            await self.db.flush()
            return existing
        point = InternalMarketSeriesPoint(
            organization_id=organization_id,
            series_type=series_type,
            station_id=station_id,
            canonical_product_id=canonical_product_id,
            distributor_id=distributor_id,
            observation_datetime=observation_datetime,
            available_at=available_at,
            value=value,
            unit=unit,
            volume_weight=volume_weight,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            source_record_hash=digest,
            created_at=datetime.now(UTC),
        )
        self.db.add(point)
        await self.db.flush()
        return point

    async def run_analysis(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
        trigger_type: str = AnalysisTriggerType.MANUAL.value,
        reprocess_of_run_id: uuid.UUID | None = None,
        reprocess_reason: str | None = None,
    ) -> MarketAnalysisRun:
        params = await self.get_or_create_parameters(organization_id, user_id)
        now = datetime.now(UTC)
        period_start = data["period_start"]
        period_end = data["period_end"]
        if isinstance(period_start, str):
            period_start = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
        if isinstance(period_end, str):
            period_end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
        data["period_start"] = period_start
        data["period_end"] = period_end
        if data.get("station_id") and isinstance(data["station_id"], str):
            data["station_id"] = uuid.UUID(data["station_id"])
        if data.get("canonical_product_id") and isinstance(data["canonical_product_id"], str):
            data["canonical_product_id"] = uuid.UUID(data["canonical_product_id"])
        if data.get("distributor_id") and isinstance(data["distributor_id"], str):
            data["distributor_id"] = uuid.UUID(data["distributor_id"])
        if data.get("external_series_id") and isinstance(data["external_series_id"], str):
            data["external_series_id"] = uuid.UUID(data["external_series_id"])

        transformation = MarketTransformation(
            data.get("transformation") or params.default_transformation
        )
        frequency = MarketFrequency(data.get("frequency") or params.default_frequency)
        alignment_policy = AlignmentPolicy(
            data.get("alignment_policy") or AlignmentPolicy.EXACT_DATE.value
        )
        lag_min = int(data.get("lag_min", params.minimum_lag))
        lag_max = int(data.get("lag_max", params.maximum_lag))

        external_points, external_meta = await self._load_external_points(
            organization_id=organization_id,
            external_series_id=data.get("external_series_id"),
            synthetic_external=data.get("synthetic_external"),
            period_start=data["period_start"],
            period_end=data["period_end"],
        )
        internal_points = await self._load_internal_points(
            organization_id=organization_id,
            internal_series_type=data["internal_series_type"],
            station_id=data.get("station_id"),
            canonical_product_id=data.get("canonical_product_id"),
            distributor_id=data.get("distributor_id"),
            period_start=data["period_start"],
            period_end=data["period_end"],
            synthetic_internal=data.get("synthetic_internal"),
        )

        run = MarketAnalysisRun(
            organization_id=organization_id,
            analysis_type=data.get("analysis_type", MarketAnalysisType.FULL.value),
            status=MarketAnalysisStatus.RUNNING.value,
            external_series_id=external_meta.get("series_id"),
            external_series_code=external_meta.get("series_code"),
            internal_series_type=data["internal_series_type"],
            station_id=data.get("station_id"),
            canonical_product_id=data.get("canonical_product_id"),
            distributor_id=data.get("distributor_id"),
            period_start=data["period_start"],
            period_end=data["period_end"],
            frequency=frequency.value,
            transformation=transformation.value,
            alignment_policy=alignment_policy.value,
            lag_min=lag_min,
            lag_max=lag_max,
            interpretive_disclaimer=DISCLAIMER,
            trigger_type=trigger_type,
            requested_by=user_id,
            reprocess_of_run_id=reprocess_of_run_id,
            reprocess_reason=reprocess_reason,
            started_at=now,
            created_at=now,
            input_snapshot={
                "disclaimer": DISCLAIMER,
                "parameters": {
                    "minimum_sample_size": params.minimum_sample_size,
                    "maximum_carry_forward_age": params.maximum_carry_forward_age,
                    "minimum_reference_change": str(params.minimum_reference_change),
                    "lag_min": lag_min,
                    "lag_max": lag_max,
                },
                "external": external_meta,
                "internal_series_type": data["internal_series_type"],
                "external_points": [
                    {
                        "observation_datetime": p.observation_datetime.isoformat(),
                        "available_at": p.available_at.isoformat(),
                        "value": str(p.value),
                    }
                    for p in external_points
                ],
                "internal_points": [
                    {
                        "observation_datetime": p.observation_datetime.isoformat(),
                        "available_at": p.available_at.isoformat(),
                        "value": str(p.value),
                    }
                    for p in internal_points
                ],
                "transformation": transformation.value,
                "alignment_policy": alignment_policy.value,
                "note": "Motor opera somente no PostgreSQL; XPERT não é consultado.",
            },
        )
        self.db.add(run)
        await self.db.flush()

        # alinhamento lag=0 para pares base
        base_pairs = align_series(
            external=external_points,
            internal=internal_points,
            alignment_policy=alignment_policy,
            maximum_carry_forward_age=params.maximum_carry_forward_age,
            lag=0,
        )
        base_pairs = apply_transformation(base_pairs, transformation)
        included = [p for p in base_pairs if p.included and p.external_transformed is not None]

        warnings: list[str] = []
        if transformation == MarketTransformation.LEVEL:
            warnings.append(
                "Transformação LEVEL sujeita a correlação espúria — preferir variação"
            )
        if transformation == MarketTransformation.BASE_100:
            warnings.append("BASE_100 é visual/comparativa; não usar como cálculo financeiro")

        quality = QualityStatus.VALID
        if len(included) < params.minimum_sample_size:
            quality = QualityStatus.INSUFFICIENT_SAMPLE
            run.status = MarketAnalysisStatus.INSUFFICIENT_SAMPLE.value
            warnings.append(
                f"Amostra {len(included)} < mínimo {params.minimum_sample_size}"
            )

        xs = [p.external_transformed for p in included if p.external_transformed is not None]
        ys = [p.internal_transformed for p in included if p.internal_transformed is not None]
        assert len(xs) == len(ys)

        pearson_coef, pearson_q, pearson_w = pearson(xs, ys)
        spearman_coef, spearman_q, spearman_w = spearman(xs, ys)
        warnings.extend(pearson_w)
        warnings.extend(spearman_w)

        # cross correlation — reconstruir séries transformadas por lag
        lag_results_payload = []
        selected_lag = None
        if quality != QualityStatus.INSUFFICIENT_SAMPLE:
            # Para cada lag, realinhar e transformar
            lag_stats = []
            for lag in range(lag_min, lag_max + 1):
                lagged = align_series(
                    external=external_points,
                    internal=internal_points,
                    alignment_policy=alignment_policy,
                    maximum_carry_forward_age=params.maximum_carry_forward_age,
                    lag=lag,
                )
                lagged = apply_transformation(lagged, transformation)
                inc = [
                    p
                    for p in lagged
                    if p.included and p.external_transformed is not None
                ]
                lx = [p.external_transformed for p in inc if p.external_transformed is not None]
                ly = [p.internal_transformed for p in inc if p.internal_transformed is not None]
                coef, qstat, _ = pearson(lx, ly)
                from app.services.market_analysis.statistics import LagResult

                lag_stats.append(
                    LagResult(
                        lag=lag,
                        coefficient=coef,
                        sample_size=len(lx),
                        quality_status=qstat,
                        warnings=[],
                    )
                )
                lag_results_payload.append(
                    {
                        "lag": lag,
                        "coefficient": str(coef) if coef is not None else None,
                        "sample_size": len(lx),
                        "quality_status": qstat.value,
                        "label": "defasagem de associação observada",
                    }
                )
            best = select_best_lag(lag_stats, minimum_sample_size=params.minimum_sample_size)
            if best:
                selected_lag = best.lag
                run.selected_lag = selected_lag

        # repasse / assimetria a partir de mudanças absolutas nos pares incluídos
        pt_events: list[dict[str, Any]] = []
        upward_ratios: list[Decimal] = []
        downward_ratios: list[Decimal] = []
        for p in included:
            if p.external_change is None or p.internal_change is None:
                continue
            ratio, pt_q = pass_through_ratio(
                p.external_change,
                p.internal_change,
                minimum_reference_change=params.minimum_reference_change,
            )
            if p.external_change > 0:
                direction = EventDirection.UPWARD.value
            elif p.external_change < 0:
                direction = EventDirection.DOWNWARD.value
            else:
                direction = EventDirection.FLAT.value
            if ratio is not None:
                if direction == EventDirection.UPWARD.value:
                    upward_ratios.append(ratio)
                elif direction == EventDirection.DOWNWARD.value:
                    downward_ratios.append(ratio)
            # elasticidade se transformação percentual
            elasticity = None
            if (
                transformation == MarketTransformation.PERCENTAGE_CHANGE
                and p.external_transformed is not None
                and p.internal_transformed is not None
            ):
                elasticity, _ = pass_through_elasticity(
                    p.external_transformed,
                    p.internal_transformed,
                    minimum_reference_change=params.minimum_reference_change,
                )
            pt_events.append(
                {
                    "direction": direction,
                    "reference_change": str(p.external_change),
                    "target_change": str(p.internal_change),
                    "ratio": str(ratio) if ratio is not None else None,
                    "elasticity": str(elasticity) if elasticity is not None else None,
                    "quality": pt_q.value,
                    "period": p.period_datetime.isoformat(),
                }
            )

        def _avg(vals: list[Decimal]) -> Decimal | None:
            if not vals:
                return None
            return (sum(vals, Decimal(0)) / Decimal(len(vals))).quantize(Decimal("0.0000000001"))

        up_avg = _avg(upward_ratios)
        down_avg = _avg(downward_ratios)
        asymmetry = None
        if up_avg is not None and down_avg is not None:
            asymmetry = (up_avg - down_avg).quantize(Decimal("0.0000000001"))

        coverage = None
        expected_days = max((data["period_end"] - data["period_start"]).days, 1)
        coverage = (Decimal(len(included)) / Decimal(expected_days) * Decimal(100)).quantize(
            Decimal("0.00000001")
        )

        if pearson_q == QualityStatus.CONSTANT_SERIES:
            quality = QualityStatus.CONSTANT_SERIES
        elif quality == QualityStatus.VALID and warnings:
            quality = QualityStatus.VALID_WITH_WARNINGS

        output = {
            "disclaimer": DISCLAIMER,
            "quality_status": quality.value,
            "warnings": warnings,
            "pearson": {
                "coefficient": str(pearson_coef) if pearson_coef is not None else None,
                "sample_size": len(xs),
                "quality": pearson_q.value,
                "interpretation": "associação linear observada",
            },
            "spearman": {
                "coefficient": str(spearman_coef) if spearman_coef is not None else None,
                "sample_size": len(xs),
                "quality": spearman_q.value,
                "interpretation": "associação monotônica observada",
            },
            "lags": lag_results_payload,
            "selected_lag": selected_lag,
            "selected_lag_label": "defasagem de maior associação observada"
            if selected_lag is not None
            else None,
            "pass_through": {
                "upward_average_ratio": str(up_avg) if up_avg is not None else None,
                "downward_average_ratio": str(down_avg) if down_avg is not None else None,
                "asymmetry": str(asymmetry) if asymmetry is not None else None,
                "events_count": len(pt_events),
                "interpretation": "repasse observado — não prova intenção comercial",
            },
            "coverage_percentage": str(coverage) if coverage is not None else None,
            "aligned_pair_count": len(included),
            "excluded_hindsight": sum(
                1 for p in base_pairs if p.exclusion_reason == "HINDSIGHT_BLOCKED_AVAILABLE_AT"
            ),
        }
        run.output_snapshot = output
        run.snapshot_hash = compute_snapshot_hash(
            {"input": run.input_snapshot, "output": output}
        )
        run.sample_size = len(xs)
        run.aligned_pair_count = len(included)
        run.warning_count = len(warnings)
        run.error_count = 1 if quality == QualityStatus.FAILED else 0
        if run.status != MarketAnalysisStatus.INSUFFICIENT_SAMPLE.value:
            run.status = MarketAnalysisStatus.COMPLETED.value
        run.finished_at = datetime.now(UTC)

        # persist results
        await self._save_result(
            run.id,
            MetricType.PEARSON,
            pearson_coef,
            len(xs),
            coverage,
            pearson_q if quality != QualityStatus.INSUFFICIENT_SAMPLE else quality,
            pearson_w,
        )
        await self._save_result(
            run.id,
            MetricType.SPEARMAN,
            spearman_coef,
            len(xs),
            coverage,
            spearman_q if quality != QualityStatus.INSUFFICIENT_SAMPLE else quality,
            spearman_w,
        )
        if selected_lag is not None:
            best_coef = next(
                (x["coefficient"] for x in lag_results_payload if x["lag"] == selected_lag),
                None,
            )
            await self._save_result(
                run.id,
                MetricType.SELECTED_LAG,
                Decimal(best_coef) if best_coef else None,
                len(xs),
                coverage,
                quality,
                [],
                lag_value=selected_lag,
            )
        for lag_row in lag_results_payload:
            await self._save_result(
                run.id,
                MetricType.CROSS_CORRELATION_LAG,
                Decimal(lag_row["coefficient"]) if lag_row["coefficient"] else None,
                lag_row["sample_size"],
                coverage,
                QualityStatus(lag_row["quality_status"]),
                [],
                lag_value=lag_row["lag"],
            )

        await self._save_result(
            run.id,
            MetricType.UPWARD_PASS_THROUGH,
            up_avg,
            len(upward_ratios),
            coverage,
            quality,
            [],
            pass_through_ratio_value=up_avg,
        )
        await self._save_result(
            run.id,
            MetricType.DOWNWARD_PASS_THROUGH,
            down_avg,
            len(downward_ratios),
            coverage,
            quality,
            [],
            pass_through_ratio_value=down_avg,
        )
        await self._save_result(
            run.id,
            MetricType.ASYMMETRY,
            asymmetry,
            len(upward_ratios) + len(downward_ratios),
            coverage,
            quality,
            [],
        )

        for p in base_pairs:
            self.db.add(
                MarketAlignedObservation(
                    analysis_run_id=run.id,
                    period_datetime=p.period_datetime,
                    external_observation_id=uuid.UUID(p.external_observation_id)
                    if p.external_observation_id
                    else None,
                    external_value=p.external_value,
                    external_change=p.external_change,
                    internal_entity_type=p.internal_entity_type,
                    internal_entity_id=uuid.UUID(p.internal_entity_id)
                    if p.internal_entity_id
                    else None,
                    internal_value=p.internal_value,
                    internal_change=p.internal_change,
                    lag_applied=p.lag_applied,
                    carry_forward=p.carry_forward,
                    carry_forward_age=p.carry_forward_age,
                    included=p.included,
                    exclusion_reason=p.exclusion_reason,
                    created_at=datetime.now(UTC),
                )
            )

        for ev in pt_events:
            if ev["quality"] == QualityStatus.PASS_THROUGH_UNAVAILABLE.value:
                continue
            self.db.add(
                MarketPassThroughEvent(
                    analysis_run_id=run.id,
                    event_type="REFERENCE_TO_TARGET",
                    event_direction=ev["direction"],
                    reference_event_datetime=datetime.fromisoformat(ev["period"]),
                    target_event_datetime=datetime.fromisoformat(ev["period"]),
                    lag_value=selected_lag or 0,
                    reference_change=Decimal(ev["reference_change"]),
                    target_change=Decimal(ev["target_change"]),
                    pass_through_ratio=Decimal(ev["ratio"]) if ev["ratio"] else None,
                    pass_through_elasticity=Decimal(ev["elasticity"])
                    if ev.get("elasticity")
                    else None,
                    quality_status=ev["quality"],
                    details={"disclaimer": DISCLAIMER},
                    created_at=datetime.now(UTC),
                )
            )

        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="market_analysis_run",
                entity_id=run.id,
                action="RUN",
                after_data={
                    "status": run.status,
                    "sample_size": run.sample_size,
                    "selected_lag": run.selected_lag,
                    "hash": run.snapshot_hash,
                },
            )
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def reprocess(
        self,
        *,
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        audit_ctx: AuditContext,
    ) -> MarketAnalysisRun:
        original = await self.get_run(run_id, organization_id)
        data = {
            "analysis_type": original.analysis_type,
            "external_series_id": original.external_series_id,
            "internal_series_type": original.internal_series_type,
            "station_id": original.station_id,
            "canonical_product_id": original.canonical_product_id,
            "distributor_id": original.distributor_id,
            "period_start": original.period_start,
            "period_end": original.period_end,
            "frequency": original.frequency,
            "transformation": original.transformation,
            "alignment_policy": original.alignment_policy,
            "lag_min": original.lag_min,
            "lag_max": original.lag_max,
        }
        # preservar pontos sintéticos do snapshot se houver
        if original.input_snapshot:
            if "synthetic_external" in (original.input_snapshot.get("external") or {}):
                data["synthetic_external"] = original.input_snapshot["external"]["synthetic_external"]
            syn_int = original.input_snapshot.get("synthetic_internal")
            if syn_int:
                data["synthetic_internal"] = syn_int
            # reconstruir a partir dos pontos do snapshot
            data["synthetic_external"] = [
                {
                    "observation_datetime": p["observation_datetime"],
                    "available_at": p["available_at"],
                    "value": p["value"],
                }
                for p in original.input_snapshot.get("external_points") or []
            ]
            data["synthetic_internal"] = [
                {
                    "observation_datetime": p["observation_datetime"],
                    "available_at": p["available_at"],
                    "value": p["value"],
                }
                for p in original.input_snapshot.get("internal_points") or []
            ]
        return await self.run_analysis(
            organization_id=organization_id,
            user_id=user_id,
            data=data,
            audit_ctx=audit_ctx,
            trigger_type=AnalysisTriggerType.REPROCESS.value,
            reprocess_of_run_id=original.id,
            reprocess_reason=reason,
        )

    async def get_run(self, run_id: uuid.UUID, organization_id: uuid.UUID) -> MarketAnalysisRun:
        run = await self.db.get(MarketAnalysisRun, run_id)
        if run is None or run.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        return run

    async def list_runs(self, organization_id: uuid.UUID, limit: int = 50) -> list[MarketAnalysisRun]:
        q = await self.db.execute(
            select(MarketAnalysisRun)
            .where(MarketAnalysisRun.organization_id == organization_id)
            .order_by(MarketAnalysisRun.started_at.desc())
            .limit(limit)
        )
        return list(q.scalars().all())

    async def list_results(self, run_id: uuid.UUID, organization_id: uuid.UUID):
        await self.get_run(run_id, organization_id)
        q = await self.db.execute(
            select(MarketAnalysisResult).where(MarketAnalysisResult.analysis_run_id == run_id)
        )
        return list(q.scalars().all())

    async def list_aligned(self, run_id: uuid.UUID, organization_id: uuid.UUID):
        await self.get_run(run_id, organization_id)
        q = await self.db.execute(
            select(MarketAlignedObservation)
            .where(MarketAlignedObservation.analysis_run_id == run_id)
            .order_by(MarketAlignedObservation.period_datetime)
        )
        return list(q.scalars().all())

    async def list_pass_through(self, run_id: uuid.UUID, organization_id: uuid.UUID):
        await self.get_run(run_id, organization_id)
        q = await self.db.execute(
            select(MarketPassThroughEvent).where(
                MarketPassThroughEvent.analysis_run_id == run_id
            )
        )
        return list(q.scalars().all())

    async def analytics_summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        runs = await self.list_runs(organization_id, limit=20)
        completed = [r for r in runs if r.status == MarketAnalysisStatus.COMPLETED.value]
        best = None
        for r in completed:
            out = r.output_snapshot or {}
            pear = (out.get("pearson") or {}).get("coefficient")
            if pear is None:
                continue
            coef = abs(Decimal(pear))
            if best is None or coef > best[0]:
                best = (coef, r)
        insufficient = sum(
            1 for r in runs if r.status == MarketAnalysisStatus.INSUFFICIENT_SAMPLE.value
        )
        return {
            "disclaimer": DISCLAIMER,
            "runs_count": len(runs),
            "completed_count": len(completed),
            "insufficient_sample_count": insufficient,
            "strongest_association": {
                "run_id": str(best[1].id) if best else None,
                "coefficient": str(best[0]) if best else None,
                "selected_lag": best[1].selected_lag if best else None,
                "label": "maior associação observada (módulo do coeficiente)",
            }
            if best
            else None,
            "note": "Homologação real bloqueada até séries externas da Sprint 9 estarem homologadas.",
        }

    async def _save_result(
        self,
        run_id: uuid.UUID,
        metric_type: MetricType,
        coefficient: Decimal | None,
        sample_size: int,
        coverage: Decimal | None,
        quality: QualityStatus,
        warnings: list[str],
        *,
        lag_value: int | None = None,
        pass_through_ratio_value: Decimal | None = None,
    ) -> None:
        self.db.add(
            MarketAnalysisResult(
                analysis_run_id=run_id,
                metric_type=metric_type.value,
                coefficient=coefficient,
                lag_value=lag_value,
                sample_size=sample_size,
                coverage_percentage=coverage,
                pass_through_ratio=pass_through_ratio_value,
                quality_status=quality.value,
                warnings=warnings or None,
                details={"disclaimer": DISCLAIMER},
                created_at=datetime.now(UTC),
            )
        )

    async def _load_external_points(
        self,
        *,
        organization_id: uuid.UUID,
        external_series_id: uuid.UUID | None,
        synthetic_external: list[dict[str, Any]] | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[list[SeriesPoint], dict[str, Any]]:
        if synthetic_external is not None:
            points = [
                SeriesPoint(
                    observation_datetime=datetime.fromisoformat(p["observation_datetime"]),
                    available_at=datetime.fromisoformat(p["available_at"]),
                    value=Decimal(str(p["value"])),
                    observation_id=None,
                )
                for p in synthetic_external
            ]
            return points, {
                "series_id": None,
                "series_code": "SYNTHETIC_EXTERNAL",
                "synthetic": True,
                "synthetic_external": True,
            }

        if external_series_id is None:
            raise HTTPException(status_code=400, detail="external_series_id ou synthetic_external obrigatório")

        series = await self.db.get(ExternalSeries, external_series_id)
        if series is None or (
            series.organization_id is not None and series.organization_id != organization_id
        ):
            raise HTTPException(status_code=404, detail="Série externa não encontrada")
        if not series.active:
            raise HTTPException(status_code=400, detail="Série externa inativa")

        q = await self.db.execute(
            select(ExternalObservation)
            .where(
                ExternalObservation.series_id == series.id,
                ExternalObservation.revision_status == "CURRENT",
                ExternalObservation.observation_datetime >= period_start,
                ExternalObservation.observation_datetime <= period_end,
            )
            .order_by(ExternalObservation.observation_datetime)
        )
        rows = list(q.scalars().all())
        points = [
            SeriesPoint(
                observation_datetime=r.observation_datetime,
                available_at=r.available_at or r.published_at or r.fetched_at,
                value=r.canonical_value,
                observation_id=str(r.id),
            )
            for r in rows
        ]
        return points, {
            "series_id": series.id,
            "series_code": series.code,
            "synthetic": False,
            "unit": series.canonical_unit,
        }

    async def _load_internal_points(
        self,
        *,
        organization_id: uuid.UUID,
        internal_series_type: str,
        station_id: uuid.UUID | None,
        canonical_product_id: uuid.UUID | None,
        distributor_id: uuid.UUID | None,
        period_start: datetime,
        period_end: datetime,
        synthetic_internal: list[dict[str, Any]] | None,
    ) -> list[SeriesPoint]:
        if synthetic_internal is not None:
            return [
                SeriesPoint(
                    observation_datetime=datetime.fromisoformat(p["observation_datetime"]),
                    available_at=datetime.fromisoformat(p["available_at"]),
                    value=Decimal(str(p["value"])),
                    entity_type=InternalSeriesType.SYNTHETIC_INTERNAL.value,
                )
                for p in synthetic_internal
            ]

        stmt = select(InternalMarketSeriesPoint).where(
            InternalMarketSeriesPoint.organization_id == organization_id,
            InternalMarketSeriesPoint.series_type == internal_series_type,
            InternalMarketSeriesPoint.observation_datetime >= period_start,
            InternalMarketSeriesPoint.observation_datetime <= period_end,
        )
        if station_id:
            stmt = stmt.where(InternalMarketSeriesPoint.station_id == station_id)
        if canonical_product_id:
            stmt = stmt.where(
                InternalMarketSeriesPoint.canonical_product_id == canonical_product_id
            )
        if distributor_id:
            stmt = stmt.where(InternalMarketSeriesPoint.distributor_id == distributor_id)
        rows = list(
            (await self.db.execute(stmt.order_by(InternalMarketSeriesPoint.observation_datetime)))
            .scalars()
            .all()
        )
        return [
            SeriesPoint(
                observation_datetime=r.observation_datetime,
                available_at=r.available_at,
                value=r.value,
                entity_type=r.source_entity_type,
                entity_id=str(r.source_entity_id) if r.source_entity_id else None,
            )
            for r in rows
        ]
