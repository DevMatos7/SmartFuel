"""Sprint 12 — métricas executivas com qualidade e freshness (sem inventar zero)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.operations_enums import FreshnessStatus, MetricQualityStatus
from app.domain.quote_comparison.snapshot_canonical import compute_snapshot_hash
from app.models.operations import ExecutiveMetricSnapshot
from app.models.station import Station
from app.services.alert_engine_service import AlertEngineService


def _card(
    *,
    code: str,
    label: str,
    value: Decimal | str | None,
    unit: str | None,
    quality: str,
    freshness: str,
    coverage: Decimal | None,
    updated_at: datetime | None,
    deep_link: str,
    source_modules: list[str],
    previous_value: Decimal | str | None = None,
) -> dict[str, Any]:
    return {
        "metric_code": code,
        "label": label,
        "value": str(value) if value is not None else None,
        "previous_value": str(previous_value) if previous_value is not None else None,
        "unit": unit,
        "quality_status": quality,
        "freshness_status": freshness,
        "coverage_percentage": str(coverage) if coverage is not None else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "deep_link": deep_link,
        "source_modules": source_modules,
        "empty_reason": None
        if value is not None
        else quality
        if quality
        in (
            MetricQualityStatus.NO_DATA,
            MetricQualityStatus.NOT_SYNCED,
            MetricQualityStatus.STALE,
            MetricQualityStatus.NOT_CONFIGURED,
            MetricQualityStatus.NOT_APPLICABLE,
            MetricQualityStatus.ERROR,
        )
        else MetricQualityStatus.NO_DATA,
    }


class ExecutiveMetricsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def persist_snapshot(
        self,
        *,
        organization_id: uuid.UUID,
        metric_code: str,
        value_numeric: Decimal | None,
        quality_status: str,
        freshness_status: str,
        period_start: datetime,
        period_end: datetime,
        station_id: uuid.UUID | None = None,
        unit: str | None = None,
        coverage: Decimal | None = None,
        source_modules: list[str] | None = None,
        value_text: str | None = None,
    ) -> ExecutiveMetricSnapshot:
        now = datetime.now(UTC)
        dimension_key = f"STATION:{station_id}" if station_id else "ORG"
        payload = {
            "organization_id": str(organization_id),
            "station_id": str(station_id) if station_id else None,
            "metric_code": metric_code,
            "value_numeric": str(value_numeric) if value_numeric is not None else None,
            "value_text": value_text,
            "quality_status": quality_status,
            "freshness_status": freshness_status,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }
        snap = ExecutiveMetricSnapshot(
            id=uuid.uuid4(),
            organization_id=organization_id,
            station_id=station_id,
            metric_code=metric_code,
            dimension_key=dimension_key,
            dimension_payload={"station_id": str(station_id)} if station_id else {},
            period_start=period_start,
            period_end=period_end,
            reference_datetime=now,
            value_numeric=value_numeric,
            value_text=value_text,
            unit=unit,
            coverage_percentage=coverage,
            quality_status=quality_status,
            freshness_status=freshness_status,
            source_modules=source_modules or [],
            source_snapshot_ids=[],
            snapshot_hash=compute_snapshot_hash(payload),
            calculated_at=now,
            created_at=now,
        )
        self.db.add(snap)
        await self.db.flush()
        return snap

    async def build_synthetic_dashboard(
        self, organization_id: uuid.UUID, station_ids: list[uuid.UUID]
    ) -> dict[str, Any]:
        """Homologação sintética — quatro postos com qualidade diversa."""
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now
        cards = []

        # volume vendido com cobertura alta
        await self.persist_snapshot(
            organization_id=organization_id,
            metric_code="SALES_VOLUME_LITERS",
            value_numeric=Decimal("125000.000"),
            quality_status=MetricQualityStatus.HIGH,
            freshness_status=FreshnessStatus.FRESH,
            period_start=start,
            period_end=end,
            unit="L",
            coverage=Decimal("95.00000000"),
            source_modules=["fuel_sales"],
        )
        cards.append(
            _card(
                code="SALES_VOLUME_LITERS",
                label="Volume vendido",
                value=Decimal("125000"),
                unit="L",
                quality=MetricQualityStatus.HIGH,
                freshness=FreshnessStatus.FRESH,
                coverage=Decimal("95"),
                updated_at=now,
                deep_link="/analytics/fuel-sales",
                source_modules=["fuel_sales"],
                previous_value=Decimal("118000"),
            )
        )

        # compras sem dados → NÃO zero
        await self.persist_snapshot(
            organization_id=organization_id,
            metric_code="PURCHASE_VOLUME_LITERS",
            value_numeric=None,
            quality_status=MetricQualityStatus.NOT_SYNCED,
            freshness_status=FreshnessStatus.NOT_SYNCED,
            period_start=start,
            period_end=end,
            unit="L",
            coverage=None,
            source_modules=["fuel_purchases"],
        )
        cards.append(
            _card(
                code="PURCHASE_VOLUME_LITERS",
                label="Volume comprado",
                value=None,
                unit="L",
                quality=MetricQualityStatus.NOT_SYNCED,
                freshness=FreshnessStatus.NOT_SYNCED,
                coverage=None,
                updated_at=now,
                deep_link="/analytics/fuel-purchases",
                source_modules=["fuel_purchases"],
            )
        )

        # margem com qualidade média / stale parcial
        await self.persist_snapshot(
            organization_id=organization_id,
            metric_code="GROSS_COMMERCIAL_MARGIN_PER_LITER",
            value_numeric=Decimal("0.4200000000"),
            quality_status=MetricQualityStatus.MEDIUM,
            freshness_status=FreshnessStatus.STALE,
            period_start=start,
            period_end=end,
            unit="BRL/L",
            coverage=Decimal("60.00000000"),
            source_modules=["pricing", "fuel_sales"],
        )
        cards.append(
            _card(
                code="GROSS_COMMERCIAL_MARGIN_PER_LITER",
                label="Margem bruta comercial / L",
                value=Decimal("0.42"),
                unit="BRL/L",
                quality=MetricQualityStatus.MEDIUM,
                freshness=FreshnessStatus.STALE,
                coverage=Decimal("60"),
                updated_at=now - timedelta(days=2),
                deep_link="/pricing/margins",
                source_modules=["pricing", "fuel_sales"],
                previous_value=Decimal("0.45"),
            )
        )

        station_rows = []
        for idx, sid in enumerate(station_ids[:4]):
            q = MetricQualityStatus.HIGH if idx % 2 == 0 else MetricQualityStatus.LOW
            f = FreshnessStatus.FRESH if idx < 3 else FreshnessStatus.STALE
            margin = Decimal("0.35") + Decimal(idx) * Decimal("0.05") if q != MetricQualityStatus.LOW else None
            await self.persist_snapshot(
                organization_id=organization_id,
                station_id=sid,
                metric_code="STATION_MARGIN_PER_LITER",
                value_numeric=margin,
                quality_status=q if margin is not None else MetricQualityStatus.NO_DATA,
                freshness_status=f,
                period_start=start,
                period_end=end,
                unit="BRL/L",
                coverage=Decimal("80") if margin is not None else None,
                source_modules=["pricing"],
            )
            station_rows.append(
                {
                    "station_id": str(sid),
                    "sales_volume": str(Decimal("10000") * (idx + 1)) if q == MetricQualityStatus.HIGH else None,
                    "margin_per_liter": str(margin) if margin is not None else None,
                    "purchase_cost_per_liter": None,
                    "avg_price": str(Decimal("5.50") + Decimal(idx) * Decimal("0.02")),
                    "open_alerts": idx,
                    "freshness_status": f,
                    "quality_status": q if margin is not None else MetricQualityStatus.NO_DATA,
                    "empty_reasons": []
                    if margin is not None
                    else [MetricQualityStatus.NO_DATA],
                }
            )

        alert_svc = AlertEngineService(self.db)
        synth_alerts = await alert_svc.create_synthetic_alerts(
            organization_id, station_ids[0] if station_ids else None
        )
        cards.extend(
            [
                _card(
                    code="CRITICAL_ALERTS",
                    label="Alertas críticos",
                    value=Decimal(sum(1 for a in synth_alerts if a["alert_code"] == "UNSAFE_XPERT_SOURCE")),
                    unit="count",
                    quality=MetricQualityStatus.HIGH,
                    freshness=FreshnessStatus.FRESH,
                    coverage=Decimal("100"),
                    updated_at=now,
                    deep_link="/executive/alerts",
                    source_modules=["alerts"],
                ),
                _card(
                    code="PENDING_APPROVALS",
                    label="Pendências de aprovação",
                    value=None,
                    unit="count",
                    quality=MetricQualityStatus.NOT_APPLICABLE,
                    freshness=FreshnessStatus.UNKNOWN,
                    coverage=None,
                    updated_at=now,
                    deep_link="/pricing/approvals",
                    source_modules=["pricing"],
                ),
                _card(
                    code="INTEGRATIONS_DELAYED",
                    label="Integrações atrasadas",
                    value=Decimal("1"),
                    unit="count",
                    quality=MetricQualityStatus.HIGH,
                    freshness=FreshnessStatus.FRESH,
                    coverage=Decimal("100"),
                    updated_at=now,
                    deep_link="/executive/integrations",
                    source_modules=["xpert"],
                ),
                _card(
                    code="MONITORED_STATIONS",
                    label="Postos monitorados",
                    value=Decimal(len(station_ids[:4])),
                    unit="count",
                    quality=MetricQualityStatus.HIGH,
                    freshness=FreshnessStatus.FRESH,
                    coverage=Decimal("100"),
                    updated_at=now,
                    deep_link="/executive/stations",
                    source_modules=["stations"],
                ),
            ]
        )

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "cards": cards,
            "by_station": station_rows,
            "disclaimer": (
                "Margem bruta comercial estimada. Ausência de dados não é zero. "
                "XPERT permanece UNSAFE (sa). Sem escrita no ERP."
            ),
            "comparison_warning": None,
            "synthetic": True,
            "alerts_seeded": synth_alerts,
        }

    async def summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(ExecutiveMetricSnapshot)
            .where(
                ExecutiveMetricSnapshot.organization_id == organization_id,
                ExecutiveMetricSnapshot.station_id.is_(None),
            )
            .order_by(ExecutiveMetricSnapshot.calculated_at.desc())
            .limit(50)
        )
        snaps = list(result.scalars().all())
        if not snaps:
            return {
                "cards": [],
                "empty": True,
                "empty_reason": MetricQualityStatus.NO_DATA,
                "disclaimer": "Sem snapshots executivos. Execute homologação sintética ou materialização.",
            }
        latest_by_code: dict[str, ExecutiveMetricSnapshot] = {}
        for s in snaps:
            if s.metric_code not in latest_by_code:
                latest_by_code[s.metric_code] = s
        cards = [
            _card(
                code=s.metric_code,
                label=s.metric_code,
                value=s.value_numeric if s.value_numeric is not None else s.value_text,
                unit=s.unit,
                quality=s.quality_status,
                freshness=s.freshness_status,
                coverage=s.coverage_percentage,
                updated_at=s.calculated_at,
                deep_link="/executive",
                source_modules=list(s.source_modules or []),
            )
            for s in latest_by_code.values()
        ]
        return {
            "cards": cards,
            "empty": False,
            "disclaimer": "KPI com qualidade e freshness. Ausência ≠ zero.",
        }

    async def by_station(self, organization_id: uuid.UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ExecutiveMetricSnapshot)
            .where(
                ExecutiveMetricSnapshot.organization_id == organization_id,
                ExecutiveMetricSnapshot.station_id.is_not(None),
                ExecutiveMetricSnapshot.metric_code == "STATION_MARGIN_PER_LITER",
            )
            .order_by(ExecutiveMetricSnapshot.calculated_at.desc())
        )
        rows = []
        seen: set[uuid.UUID] = set()
        for s in result.scalars().all():
            if s.station_id in seen:
                continue
            seen.add(s.station_id)  # type: ignore[arg-type]
            rows.append(
                {
                    "station_id": str(s.station_id),
                    "margin_per_liter": str(s.value_numeric) if s.value_numeric is not None else None,
                    "quality_status": s.quality_status,
                    "freshness_status": s.freshness_status,
                    "coverage_percentage": str(s.coverage_percentage)
                    if s.coverage_percentage is not None
                    else None,
                    "updated_at": s.calculated_at.isoformat(),
                }
            )
        return rows

    async def data_quality(self, organization_id: uuid.UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(ExecutiveMetricSnapshot).where(
                ExecutiveMetricSnapshot.organization_id == organization_id
            )
        )
        snaps = list(result.scalars().all())
        by_q: dict[str, int] = {}
        for s in snaps:
            by_q[s.quality_status] = by_q.get(s.quality_status, 0) + 1
        return {"by_quality_status": by_q, "total": len(snaps)}

    async def freshness(self, organization_id: uuid.UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(ExecutiveMetricSnapshot).where(
                ExecutiveMetricSnapshot.organization_id == organization_id
            )
        )
        snaps = list(result.scalars().all())
        by_f: dict[str, int] = {}
        for s in snaps:
            by_f[s.freshness_status] = by_f.get(s.freshness_status, 0) + 1
        return {
            "by_freshness_status": by_f,
            "note": "Enquanto scheduler XPERT estiver bloqueado, freshness depende de sync manual.",
        }

    async def list_station_ids(self, organization_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(Station.id).where(Station.organization_id == organization_id, Station.active.is_(True))
        )
        return list(result.scalars().all())
