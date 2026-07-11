"""Analytics e overrides — Sprint 8 purchase benchmarks."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.purchase_benchmark_enums import (
    BenchmarkDecisionResult,
    BenchmarkItemStatus,
    BenchmarkOverrideType,
)
from app.models.fuel_purchases import FuelPurchaseInvoice
from app.models.purchase_benchmarks import (
    PurchaseBenchmarkOverride,
    PurchaseBenchmarkParameter,
    PurchaseQuoteBenchmarkCandidate,
    PurchaseQuoteBenchmarkItem,
    PurchaseQuoteBenchmarkRun,
)
from app.services.purchase_quote_benchmark_service import PurchaseQuoteBenchmarkService

_ZERO = Decimal("0")


class PurchaseBenchmarkAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
        include_opportunity: bool,
    ) -> dict[str, Any]:
        items = await self._latest_items(organization_id, station_ids, date_from, date_to)
        volume = sum((i.volume_liters or _ZERO for i in items), _ZERO)
        bench_items = [
            i
            for i in items
            if i.benchmark_status
            in {BenchmarkItemStatus.BENCHMARKED, BenchmarkItemStatus.BENCHMARKED_WITH_WARNINGS}
        ]
        bench_vol = sum((i.volume_liters or _ZERO for i in bench_items), _ZERO)
        actual = sum((i.actual_delivered_cost or _ZERO for i in items), _ZERO)
        bench_cost = sum((i.benchmark_total_cost or _ZERO for i in bench_items), _ZERO)
        variance = sum((i.cost_variance_amount or _ZERO for i in bench_items), _ZERO)
        opportunity = sum((i.opportunity_amount or _ZERO for i in bench_items), _ZERO)
        best = sum(1 for i in bench_items if i.decision_result == BenchmarkDecisionResult.BEST_OR_TIED)
        return {
            "purchase_group_count": len(items),
            "benchmarked_group_count": len(bench_items),
            "purchased_volume_liters": volume,
            "benchmarked_volume_liters": bench_vol,
            "coverage_volume_ratio": (bench_vol / volume) if volume > 0 else None,
            "actual_total_cost": actual,
            "benchmark_total_cost": bench_cost if bench_items else None,
            "cost_variance_amount": variance if bench_items else None,
            "opportunity_amount": opportunity if include_opportunity and bench_items else None,
            "best_or_tied_count": best,
        }

    async def coverage(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        items = await self._latest_items(organization_id, station_ids, date_from, date_to)
        total = len(items)
        volume = sum((i.volume_liters or _ZERO for i in items), _ZERO)
        value = sum((i.actual_delivered_cost or _ZERO for i in items), _ZERO)
        by_status: dict[str, dict[str, Any]] = {}
        for i in items:
            bucket = by_status.setdefault(
                i.benchmark_status,
                {"count": 0, "volume_liters": _ZERO, "value": _ZERO},
            )
            bucket["count"] += 1
            bucket["volume_liters"] += i.volume_liters or _ZERO
            bucket["value"] += i.actual_delivered_cost or _ZERO
        return {
            "total_groups": total,
            "total_volume_liters": volume,
            "total_value": value,
            "by_status": {
                k: {
                    "count": v["count"],
                    "volume_liters": v["volume_liters"],
                    "value": v["value"],
                    "count_ratio": (v["count"] / total) if total else None,
                    "volume_ratio": (v["volume_liters"] / volume) if volume > 0 else None,
                    "value_ratio": (v["value"] / value) if value > 0 else None,
                }
                for k, v in by_status.items()
            },
        }

    async def data_quality(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        items = await self._latest_items(organization_id, station_ids, date_from, date_to)
        def count(status: str) -> int:
            return sum(1 for i in items if i.benchmark_status == status)

        return {
            "unmapped_product_count": count(BenchmarkItemStatus.UNMAPPED_PRODUCT),
            "unmapped_supplier_warning_count": sum(
                1
                for i in items
                if i.warnings
                and any(
                    (w.get("code") if isinstance(w, dict) else None)
                    == BenchmarkItemStatus.UNMAPPED_ACTUAL_SUPPLIER
                    for w in i.warnings
                )
            ),
            "missing_cost_count": count(BenchmarkItemStatus.MISSING_ACTUAL_COST),
            "missing_volume_count": count(BenchmarkItemStatus.MISSING_VOLUME),
            "reference_unavailable_count": count(BenchmarkItemStatus.REFERENCE_TIME_UNAVAILABLE),
            "no_quotes_count": count(BenchmarkItemStatus.NO_QUOTES_AVAILABLE),
            "no_eligible_count": count(BenchmarkItemStatus.NO_ELIGIBLE_QUOTES),
            "not_comparable_count": count(BenchmarkItemStatus.NOT_COMPARABLE),
            "low_confidence_count": sum(
                1
                for i in items
                if i.warnings
                and any(
                    (w.get("code") if isinstance(w, dict) else None) == "REFERENCE_WARNING"
                    for w in i.warnings
                )
            ),
        }

    async def opportunities(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        items = await self._latest_items(organization_id, station_ids, date_from, date_to)
        ranked = sorted(
            [i for i in items if (i.opportunity_amount or _ZERO) > 0],
            key=lambda x: x.opportunity_amount or _ZERO,
            reverse=True,
        )[:limit]
        return [
            {
                "benchmark_item_id": i.id,
                "purchase_invoice_id": i.purchase_invoice_id,
                "station_id": i.station_id,
                "canonical_product_id": i.canonical_product_id,
                "volume_liters": i.volume_liters,
                "opportunity_amount": i.opportunity_amount,
                "cost_variance_per_liter": i.cost_variance_per_liter,
                "decision_result": i.decision_result,
            }
            for i in ranked
        ]

    async def export_csv(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
        include_opportunity: bool,
    ) -> str:
        items = await self._latest_items(organization_id, station_ids, date_from, date_to)
        buf = io.StringIO()
        writer = csv.writer(buf)
        headers = [
            "benchmark_item_id",
            "purchase_invoice_id",
            "station_id",
            "product_id",
            "volume_liters",
            "actual_per_liter",
            "benchmark_per_liter",
            "variance_per_liter",
            "decision",
            "status",
        ]
        if include_opportunity:
            headers.append("opportunity_amount")
        writer.writerow(headers)
        for i in items:
            row = [
                str(i.id),
                str(i.purchase_invoice_id),
                str(i.station_id),
                str(i.canonical_product_id) if i.canonical_product_id else "",
                str(i.volume_liters),
                str(i.actual_delivered_cost_per_liter or ""),
                str(i.benchmark_cost_per_liter or ""),
                str(i.cost_variance_per_liter or ""),
                i.decision_result,
                i.benchmark_status,
            ]
            if include_opportunity:
                row.append(str(i.opportunity_amount or ""))
            writer.writerow(row)
        return buf.getvalue()

    async def get_run(
        self, *, organization_id: uuid.UUID, run_id: uuid.UUID, station_ids: list[uuid.UUID]
    ) -> PurchaseQuoteBenchmarkRun | None:
        return (
            await self.db.execute(
                select(PurchaseQuoteBenchmarkRun).where(
                    PurchaseQuoteBenchmarkRun.id == run_id,
                    PurchaseQuoteBenchmarkRun.organization_id == organization_id,
                    PurchaseQuoteBenchmarkRun.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()

    async def list_runs(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        invoice_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PurchaseQuoteBenchmarkRun], int]:
        filters = [
            PurchaseQuoteBenchmarkRun.organization_id == organization_id,
            PurchaseQuoteBenchmarkRun.station_id.in_(station_ids),
        ]
        if invoice_id:
            filters.append(PurchaseQuoteBenchmarkRun.purchase_invoice_id == invoice_id)
        total = (
            await self.db.execute(
                select(func.count()).select_from(PurchaseQuoteBenchmarkRun).where(*filters)
            )
        ).scalar_one()
        rows = (
            await self.db.execute(
                select(PurchaseQuoteBenchmarkRun)
                .where(*filters)
                .order_by(PurchaseQuoteBenchmarkRun.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return list(rows), int(total)

    async def list_run_items(self, run_id: uuid.UUID) -> list[PurchaseQuoteBenchmarkItem]:
        return list(
            (
                await self.db.execute(
                    select(PurchaseQuoteBenchmarkItem).where(
                        PurchaseQuoteBenchmarkItem.benchmark_run_id == run_id
                    )
                )
            ).scalars().all()
        )

    async def list_candidates(self, item_id: uuid.UUID) -> list[PurchaseQuoteBenchmarkCandidate]:
        return list(
            (
                await self.db.execute(
                    select(PurchaseQuoteBenchmarkCandidate)
                    .where(PurchaseQuoteBenchmarkCandidate.benchmark_item_id == item_id)
                    .order_by(PurchaseQuoteBenchmarkCandidate.ranking_position.nulls_last())
                )
            ).scalars().all()
        )

    async def latest_for_invoice(
        self, *, organization_id: uuid.UUID, invoice_id: uuid.UUID, station_ids: list[uuid.UUID]
    ) -> PurchaseQuoteBenchmarkRun | None:
        return (
            await self.db.execute(
                select(PurchaseQuoteBenchmarkRun)
                .where(
                    PurchaseQuoteBenchmarkRun.organization_id == organization_id,
                    PurchaseQuoteBenchmarkRun.purchase_invoice_id == invoice_id,
                    PurchaseQuoteBenchmarkRun.station_id.in_(station_ids),
                )
                .order_by(PurchaseQuoteBenchmarkRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def create_override(
        self,
        *,
        organization_id: uuid.UUID,
        invoice_id: uuid.UUID,
        override_type: str,
        new_value: dict,
        reason: str,
        created_by: uuid.UUID,
        previous_value: dict | None = None,
    ) -> PurchaseBenchmarkOverride:
        row = PurchaseBenchmarkOverride(
            id=uuid.uuid4(),
            organization_id=organization_id,
            purchase_invoice_id=invoice_id,
            override_type=override_type,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def deactivate_override(
        self, *, organization_id: uuid.UUID, override_id: uuid.UUID
    ) -> PurchaseBenchmarkOverride | None:
        row = (
            await self.db.execute(
                select(PurchaseBenchmarkOverride).where(
                    PurchaseBenchmarkOverride.id == override_id,
                    PurchaseBenchmarkOverride.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        row.deactivated_at = datetime.now(UTC)
        await self.db.flush()
        return row

    async def upsert_parameters(
        self,
        *,
        organization_id: uuid.UUID,
        absolute_tolerance_per_liter: Decimal,
        percentage_tolerance: Decimal,
        allow_low_confidence_reference: bool,
        default_comparison_mode: str,
        created_by: uuid.UUID | None,
    ) -> PurchaseBenchmarkParameter:
        now = datetime.now(UTC)
        current = (
            await self.db.execute(
                select(PurchaseBenchmarkParameter)
                .where(
                    PurchaseBenchmarkParameter.organization_id == organization_id,
                    PurchaseBenchmarkParameter.valid_until.is_(None),
                )
                .order_by(PurchaseBenchmarkParameter.valid_from.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if current is not None:
            current.valid_until = now
            current.active = False
        row = PurchaseBenchmarkParameter(
            id=uuid.uuid4(),
            organization_id=organization_id,
            absolute_tolerance_per_liter=absolute_tolerance_per_liter,
            percentage_tolerance=percentage_tolerance,
            allow_low_confidence_reference=allow_low_confidence_reference,
            default_comparison_mode=default_comparison_mode,
            valid_from=now,
            valid_until=None,
            active=True,
            created_by=created_by,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def _latest_items(
        self,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date | None,
        date_to: date | None,
    ) -> list[PurchaseQuoteBenchmarkItem]:
        # latest run per invoice, then its items
        run_filters = [
            PurchaseQuoteBenchmarkRun.organization_id == organization_id,
            PurchaseQuoteBenchmarkRun.station_id.in_(station_ids),
        ]
        runs = (
            await self.db.execute(
                select(PurchaseQuoteBenchmarkRun)
                .where(*run_filters)
                .order_by(PurchaseQuoteBenchmarkRun.created_at.desc())
            )
        ).scalars().all()
        latest_by_invoice: dict[uuid.UUID, PurchaseQuoteBenchmarkRun] = {}
        for run in runs:
            if run.purchase_invoice_id not in latest_by_invoice:
                latest_by_invoice[run.purchase_invoice_id] = run
        if not latest_by_invoice:
            return []

        if date_from or date_to:
            inv_q = select(FuelPurchaseInvoice.id).where(
                FuelPurchaseInvoice.id.in_(list(latest_by_invoice.keys()))
            )
            if date_from:
                inv_q = inv_q.where(FuelPurchaseInvoice.entry_date >= date_from)
            if date_to:
                inv_q = inv_q.where(FuelPurchaseInvoice.entry_date <= date_to)
            allowed = set((await self.db.execute(inv_q)).scalars().all())
            run_ids = [r.id for inv, r in latest_by_invoice.items() if inv in allowed]
        else:
            run_ids = [r.id for r in latest_by_invoice.values()]

        if not run_ids:
            return []
        return list(
            (
                await self.db.execute(
                    select(PurchaseQuoteBenchmarkItem).where(
                        PurchaseQuoteBenchmarkItem.benchmark_run_id.in_(run_ids)
                    )
                )
            ).scalars().all()
        )
