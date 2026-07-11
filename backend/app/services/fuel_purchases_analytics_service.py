from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.accounts_payable import aging_bucket, weighted_term_days
from app.core.fuel_purchases_enums import (
    AccountsPayableNormalizedStatus,
    AgingBucket,
    FuelPurchasesFreshnessStatus,
    NfeReconciliationStatus,
    PurchaseMetricEligibilityStatus,
)
from app.core.xpert_sync_enums import ErpDatasetCode, ErpSecurityStatus, ErpSyncRunStatus
from app.models.distributor import Distributor
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.fuel_purchases import (
    AccountsPayableTitle,
    FuelPurchaseDailyMetric,
    FuelPurchaseInvoice,
    FuelPurchaseItem,
    NfeXmlDocument,
)
from app.models.product import Product
from app.models.station import Station

_ZERO = Decimal("0")


def _d(value: Any) -> Decimal:
    if value is None:
        return _ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class FuelPurchasesAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
        include_cost: bool = True,
    ) -> dict[str, Any]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        volume = sum((_d(m.purchased_volume_liters) for m in metrics), _ZERO)
        gross = sum((_d(m.gross_purchase_amount) for m in metrics), _ZERO)
        delivered = sum((_d(m.commercial_delivered_cost) for m in metrics), _ZERO)
        freight = sum((_d(m.freight_amount) for m in metrics), _ZERO)
        discount = sum((_d(m.discount_amount) for m in metrics), _ZERO)
        erp_cost = sum((_d(m.erp_recorded_cost) for m in metrics if m.erp_recorded_cost is not None), _ZERO)
        invoice_count = sum((m.invoice_count for m in metrics), 0)
        avg = (delivered / volume) if volume > 0 else None

        open_payable = await self._open_payable(organization_id, station_ids)
        term = await self._weighted_term(organization_id, station_ids, date_from, date_to)

        return {
            "purchased_volume_liters": volume,
            "gross_purchase_amount": gross,
            "commercial_delivered_cost": delivered if include_cost else None,
            "average_delivered_cost_per_liter": avg if include_cost else None,
            "total_freight_amount": freight,
            "total_discount_amount": discount,
            "invoice_count": invoice_count,
            "weighted_term_days": term,
            "open_payable_amount": open_payable,
            "erp_recorded_cost": erp_cost if include_cost and erp_cost > 0 else None,
        }

    async def trend(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        by_date: dict[date, dict[str, Decimal | int]] = {}
        for m in metrics:
            bucket = by_date.setdefault(
                m.business_date,
                {
                    "volume": _ZERO,
                    "gross": _ZERO,
                    "delivered": _ZERO,
                    "freight": _ZERO,
                },
            )
            bucket["volume"] = _d(bucket["volume"]) + _d(m.purchased_volume_liters)
            bucket["gross"] = _d(bucket["gross"]) + _d(m.gross_purchase_amount)
            bucket["delivered"] = _d(bucket["delivered"]) + _d(m.commercial_delivered_cost)
            bucket["freight"] = _d(bucket["freight"]) + _d(m.freight_amount)

        rows = []
        for d in sorted(by_date):
            b = by_date[d]
            vol = _d(b["volume"])
            delivered = _d(b["delivered"])
            rows.append(
                {
                    "business_date": d,
                    "purchased_volume_liters": vol,
                    "gross_purchase_amount": _d(b["gross"]),
                    "commercial_delivered_cost": delivered,
                    "average_delivered_cost_per_liter": (delivered / vol) if vol > 0 else None,
                    "freight_amount": _d(b["freight"]),
                }
            )
        return rows

    async def by_product(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        product_ids = {m.canonical_product_id for m in metrics if m.canonical_product_id}
        names = await self._product_names(product_ids)
        agg: dict[uuid.UUID | None, dict[str, Any]] = {}
        for m in metrics:
            key = m.canonical_product_id
            row = agg.setdefault(
                key,
                {"volume": _ZERO, "gross": _ZERO, "delivered": _ZERO},
            )
            row["volume"] += _d(m.purchased_volume_liters)
            row["gross"] += _d(m.gross_purchase_amount)
            row["delivered"] += _d(m.commercial_delivered_cost)
        out = []
        for pid, row in agg.items():
            vol = row["volume"]
            delivered = row["delivered"]
            out.append(
                {
                    "product_id": pid,
                    "product_name": names.get(pid, "Não mapeado") if pid else "Não mapeado",
                    "purchased_volume_liters": vol,
                    "gross_purchase_amount": row["gross"],
                    "commercial_delivered_cost": delivered,
                    "average_delivered_cost_per_liter": (delivered / vol) if vol > 0 else None,
                }
            )
        return sorted(out, key=lambda r: r["purchased_volume_liters"], reverse=True)

    async def by_distributor(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        dist_ids = {m.distributor_id for m in metrics if m.distributor_id}
        names = await self._distributor_names(dist_ids)
        agg: dict[uuid.UUID | None, dict[str, Any]] = {}
        for m in metrics:
            key = m.distributor_id
            row = agg.setdefault(
                key,
                {"volume": _ZERO, "gross": _ZERO, "delivered": _ZERO, "invoices": 0},
            )
            row["volume"] += _d(m.purchased_volume_liters)
            row["gross"] += _d(m.gross_purchase_amount)
            row["delivered"] += _d(m.commercial_delivered_cost)
            row["invoices"] += m.invoice_count
        out = []
        for did, row in agg.items():
            vol = row["volume"]
            delivered = row["delivered"]
            out.append(
                {
                    "distributor_id": did,
                    "distributor_name": names.get(did, "Não mapeado") if did else "Não mapeado",
                    "purchased_volume_liters": vol,
                    "gross_purchase_amount": row["gross"],
                    "commercial_delivered_cost": delivered,
                    "average_delivered_cost_per_liter": (delivered / vol) if vol > 0 else None,
                    "invoice_count": row["invoices"],
                }
            )
        return sorted(out, key=lambda r: r["gross_purchase_amount"], reverse=True)

    async def by_station(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        names = await self._station_names(set(station_ids))
        agg: dict[uuid.UUID, dict[str, Any]] = {}
        for m in metrics:
            row = agg.setdefault(
                m.station_id,
                {"volume": _ZERO, "gross": _ZERO, "delivered": _ZERO, "invoices": 0},
            )
            row["volume"] += _d(m.purchased_volume_liters)
            row["gross"] += _d(m.gross_purchase_amount)
            row["delivered"] += _d(m.commercial_delivered_cost)
            row["invoices"] += m.invoice_count
        return [
            {
                "station_id": sid,
                "station_name": names.get(sid, str(sid)),
                "purchased_volume_liters": row["volume"],
                "gross_purchase_amount": row["gross"],
                "commercial_delivered_cost": row["delivered"],
                "invoice_count": row["invoices"],
            }
            for sid, row in agg.items()
        ]

    async def costs(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        volume = sum((_d(m.purchased_volume_liters) for m in metrics), _ZERO)
        delivered = sum((_d(m.commercial_delivered_cost) for m in metrics), _ZERO)
        erp = sum((_d(m.erp_recorded_cost) for m in metrics if m.erp_recorded_cost is not None), _ZERO)
        return {
            "purchased_volume_liters": volume,
            "gross_purchase_amount": sum((_d(m.gross_purchase_amount) for m in metrics), _ZERO),
            "discount_amount": sum((_d(m.discount_amount) for m in metrics), _ZERO),
            "freight_amount": sum((_d(m.freight_amount) for m in metrics), _ZERO),
            "insurance_amount": _ZERO,
            "other_expenses_amount": sum((_d(m.other_expenses_amount) for m in metrics), _ZERO),
            "commercial_delivered_cost": delivered,
            "erp_recorded_cost": erp if erp > 0 else None,
            "average_delivered_cost_per_liter": (delivered / volume) if volume > 0 else None,
            "invoice_count": sum((m.invoice_count for m in metrics), 0),
            "item_count": sum((m.item_count for m in metrics), 0),
        }

    async def data_quality(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        metrics = await self._metrics_q(organization_id, station_ids, date_from, date_to)
        unmapped_items = sum((m.unmapped_item_count for m in metrics), 0)
        unmapped_vol = sum((_d(m.unmapped_volume_liters) for m in metrics), _ZERO)
        missing_cost = sum((m.missing_cost_item_count for m in metrics), 0)

        inv_q = await self.db.execute(
            select(FuelPurchaseInvoice).where(
                FuelPurchaseInvoice.organization_id == organization_id,
                FuelPurchaseInvoice.station_id.in_(station_ids),
                FuelPurchaseInvoice.entry_date >= date_from,
                FuelPurchaseInvoice.entry_date <= date_to,
            )
        )
        invoices = list(inv_q.scalars().all())
        unmapped_supplier = sum(
            1
            for i in invoices
            if i.erp_supplier_id is None or i.distributor_id is None
        )
        xml_q = await self.db.execute(
            select(NfeXmlDocument).where(
                NfeXmlDocument.organization_id == organization_id,
                NfeXmlDocument.station_id.in_(station_ids),
            )
        )
        xmls = list(xml_q.scalars().all())
        mismatch = sum(
            1 for x in xmls if x.reconciliation_status == NfeReconciliationStatus.MISMATCH.value
        )
        missing_xml = sum(1 for i in invoices if i.access_key and not any(x.purchase_invoice_id == i.id for x in xmls))
        invalid_key = sum(
            1 for i in invoices if i.access_key and (len(i.access_key) != 44 or not i.access_key.isdigit())
        )

        return {
            "unmapped_item_count": unmapped_items,
            "unmapped_volume_liters": unmapped_vol,
            "unmapped_supplier_count": unmapped_supplier,
            "missing_cost_item_count": missing_cost,
            "missing_xml_count": missing_xml,
            "xml_mismatch_count": mismatch,
            "invalid_access_key_count": invalid_key,
            "quarantined_item_count": 0,
        }

    async def freshness(self, *, organization_id: uuid.UUID) -> dict[str, Any]:
        source = (
            await self.db.execute(select(ErpSource).where(ErpSource.organization_id == organization_id).limit(1))
        ).scalar_one_or_none()
        security = source.security_status if source else None
        if security == ErpSecurityStatus.UNSAFE.value:
            status = FuelPurchasesFreshnessStatus.UNSAFE_SOURCE.value
        else:
            status = FuelPurchasesFreshnessStatus.UNAVAILABLE.value

        run = (
            await self.db.execute(
                select(ErpSyncRun)
                .where(
                    ErpSyncRun.organization_id == organization_id,
                    ErpSyncRun.dataset_code.in_(
                        [
                            ErpDatasetCode.FUEL_PURCHASE_INVOICES.value,
                            ErpDatasetCode.FUEL_PURCHASE_ITEMS.value,
                        ]
                    ),
                    ErpSyncRun.status == ErpSyncRunStatus.COMPLETED.value,
                )
                .order_by(ErpSyncRun.finished_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if run and run.finished_at and security != ErpSecurityStatus.UNSAFE.value:
            age = datetime.utcnow() - run.finished_at.replace(tzinfo=None)
            if age <= timedelta(hours=6):
                status = FuelPurchasesFreshnessStatus.UPDATED.value
            elif age <= timedelta(hours=24):
                status = FuelPurchasesFreshnessStatus.DELAYED.value
            else:
                status = FuelPurchasesFreshnessStatus.STALE.value

        return {
            "status": status,
            "security_status": security,
            "last_completed_run_at": run.finished_at if run else None,
        }

    async def list_invoices(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
        q: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = [
            FuelPurchaseInvoice.organization_id == organization_id,
            FuelPurchaseInvoice.station_id.in_(station_ids),
        ]
        if date_from:
            filters.append(FuelPurchaseInvoice.entry_date >= date_from)
        if date_to:
            filters.append(FuelPurchaseInvoice.entry_date <= date_to)
        if q:
            filters.append(
                or_(
                    FuelPurchaseInvoice.source_document_number.ilike(f"%{q}%"),
                    FuelPurchaseInvoice.access_key.ilike(f"%{q}%"),
                )
            )
        total = (
            await self.db.execute(select(func.count()).select_from(FuelPurchaseInvoice).where(*filters))
        ).scalar_one()
        rows = (
            await self.db.execute(
                select(FuelPurchaseInvoice)
                .where(*filters)
                .order_by(FuelPurchaseInvoice.entry_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        station_names = await self._station_names({r.station_id for r in rows})
        dist_names = await self._distributor_names({r.distributor_id for r in rows if r.distributor_id})
        xml_map = await self._xml_by_invoice({r.id for r in rows})
        item_stats = await self._item_stats_by_invoice({r.id for r in rows})
        out = []
        for inv in rows:
            stats = item_stats.get(inv.id, {"volume": _ZERO, "delivered": _ZERO})
            vol = stats["volume"]
            delivered = stats["delivered"]
            xml = xml_map.get(inv.id)
            out.append(
                {
                    "id": inv.id,
                    "station_id": inv.station_id,
                    "station_name": station_names.get(inv.station_id, str(inv.station_id)),
                    "source_document_number": inv.source_document_number,
                    "source_series": inv.source_series,
                    "access_key": inv.access_key,
                    "entry_date": inv.entry_date,
                    "issue_date": inv.issue_date,
                    "distributor_name": dist_names.get(inv.distributor_id) if inv.distributor_id else None,
                    "purchased_volume_liters": vol,
                    "total_amount": inv.total_amount,
                    "delivered_cost_per_liter": (delivered / vol) if vol > 0 else None,
                    "has_xml": xml is not None,
                    "xml_imported_in_erp": bool(inv.xml_imported_in_erp),
                    "xml_reconciliation_status": xml.reconciliation_status if xml else None,
                    "metric_eligibility_status": inv.metric_eligibility_status,
                    "is_cancelled": inv.is_cancelled,
                }
            )
        return out, int(total)

    async def invoice_detail(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], invoice_id: uuid.UUID
    ) -> dict[str, Any] | None:
        inv = (
            await self.db.execute(
                select(FuelPurchaseInvoice).where(
                    FuelPurchaseInvoice.id == invoice_id,
                    FuelPurchaseInvoice.organization_id == organization_id,
                    FuelPurchaseInvoice.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()
        if inv is None:
            return None
        station_names = await self._station_names({inv.station_id})
        dist_names = await self._distributor_names({inv.distributor_id} if inv.distributor_id else set())
        stats = (await self._item_stats_by_invoice({inv.id})).get(inv.id, {"volume": _ZERO, "delivered": _ZERO})
        vol = stats["volume"]
        delivered = stats["delivered"]
        xml = (await self._xml_by_invoice({inv.id})).get(inv.id)
        return {
            "id": inv.id,
            "station_id": inv.station_id,
            "station_name": station_names.get(inv.station_id, str(inv.station_id)),
            "source_invoice_id": inv.source_invoice_id,
            "source_document_number": inv.source_document_number,
            "source_series": inv.source_series,
            "access_key": inv.access_key,
            "xml_imported_in_erp": bool(inv.xml_imported_in_erp),
            "has_xml_file": xml is not None,
            "distributor_id": inv.distributor_id,
            "distributor_name": dist_names.get(inv.distributor_id) if inv.distributor_id else None,
            "source_supplier_id": inv.source_supplier_id,
            "issue_date": inv.issue_date,
            "entry_date": inv.entry_date,
            "operation_type": inv.operation_type,
            "source_status": inv.source_status,
            "is_cancelled": inv.is_cancelled,
            "gross_amount": inv.gross_amount,
            "discount_amount": inv.discount_amount,
            "freight_amount": inv.freight_amount,
            "insurance_amount": inv.insurance_amount,
            "other_expenses_amount": inv.other_expenses_amount,
            "tax_amount": inv.tax_amount,
            "total_amount": inv.total_amount,
            "purchased_volume_liters": vol,
            "commercial_delivered_cost": delivered,
            "average_delivered_cost_per_liter": (delivered / vol) if vol > 0 else None,
            "allocation_method": inv.allocation_method,
            "metric_eligibility_status": inv.metric_eligibility_status,
            "metric_exclusion_reasons": inv.metric_exclusion_reasons,
            "payment_condition_id": inv.payment_condition_id,
        }

    async def invoice_items(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], invoice_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        items = (
            await self.db.execute(
                select(FuelPurchaseItem).where(
                    FuelPurchaseItem.purchase_invoice_id == invoice_id,
                    FuelPurchaseItem.organization_id == organization_id,
                    FuelPurchaseItem.station_id.in_(station_ids),
                )
            )
        ).scalars().all()
        names = await self._product_names({i.canonical_product_id for i in items if i.canonical_product_id})
        return [
            {
                "id": i.id,
                "source_description": i.source_description,
                "product_name": names.get(i.canonical_product_id) if i.canonical_product_id else None,
                "source_product_id": i.source_product_id,
                "volume_liters": i.volume_liters,
                "source_quantity": i.source_quantity,
                "source_unit": i.source_unit,
                "unit_price": i.unit_price,
                "gross_item_amount": i.gross_item_amount,
                "discount_amount": i.discount_amount,
                "allocated_freight_amount": i.allocated_freight_amount,
                "allocated_insurance_amount": i.allocated_insurance_amount,
                "allocated_other_expenses": i.allocated_other_expenses,
                "commercial_delivered_cost": i.commercial_delivered_cost,
                "delivered_cost_per_liter": i.delivered_cost_per_liter,
                "erp_recorded_cost": i.erp_recorded_cost,
                "accounting_cost": i.accounting_cost,
                "icms_amount": i.icms_amount,
                "icms_st_amount": i.icms_st_amount,
                "fcp_amount": i.fcp_amount,
                "pis_amount": i.pis_amount,
                "cofins_amount": i.cofins_amount,
                "cfop": i.cfop,
                "ncm": i.ncm,
                "metric_eligibility_status": i.metric_eligibility_status,
                "metric_exclusion_reasons": i.metric_exclusion_reasons,
            }
            for i in items
        ]

    async def invoice_titles(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], invoice_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        titles = (
            await self.db.execute(
                select(AccountsPayableTitle).where(
                    AccountsPayableTitle.purchase_invoice_id == invoice_id,
                    AccountsPayableTitle.organization_id == organization_id,
                    AccountsPayableTitle.station_id.in_(station_ids),
                )
            )
        ).scalars().all()
        return [
            {
                "id": t.id,
                "installment_number": t.installment_number,
                "document_number": t.document_number,
                "due_date": t.due_date,
                "payment_date": t.payment_date,
                "original_amount": t.original_amount,
                "paid_amount": t.paid_amount,
                "open_amount": t.open_amount,
                "normalized_status": t.normalized_status,
                "source_status": t.source_status,
            }
            for t in titles
        ]

    async def invoice_xml(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], invoice_id: uuid.UUID
    ) -> dict[str, Any]:
        doc = (
            await self.db.execute(
                select(NfeXmlDocument).where(
                    NfeXmlDocument.purchase_invoice_id == invoice_id,
                    NfeXmlDocument.organization_id == organization_id,
                    NfeXmlDocument.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            return {
                "id": None,
                "access_key": None,
                "parse_status": None,
                "reconciliation_status": NfeReconciliationStatus.XML_MISSING.value,
                "reconciliation_details": None,
                "xml_size_bytes": None,
                "imported_at": None,
            }
        return {
            "id": doc.id,
            "access_key": doc.access_key,
            "parse_status": doc.parse_status,
            "reconciliation_status": doc.reconciliation_status,
            "reconciliation_details": doc.reconciliation_details,
            "xml_size_bytes": doc.xml_size_bytes,
            "imported_at": doc.imported_at,
        }

    async def ap_summary(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], today: date | None = None
    ) -> dict[str, Any]:
        today = today or date.today()
        titles = await self._open_titles(organization_id, station_ids)
        open_amount = sum((_d(t.open_amount) for t in titles), _ZERO)
        overdue = sum((_d(t.open_amount) for t in titles if t.due_date < today), _ZERO)
        due7 = sum((_d(t.open_amount) for t in titles if 0 <= (t.due_date - today).days <= 7), _ZERO)
        due30 = sum((_d(t.open_amount) for t in titles if 0 <= (t.due_date - today).days <= 30), _ZERO)
        partial = sum(
            1 for t in titles if t.normalized_status == AccountsPayableNormalizedStatus.PARTIALLY_PAID.value
        )
        amounts = [_d(t.original_amount) for t in titles if t.issue_date or True]
        # Prazo médio: due_date - entry/issue quando disponível; senão due - today abs não.
        days_list: list[int] = []
        amt_list: list[Decimal] = []
        for t in titles:
            base = t.issue_date
            if base is None:
                continue
            amt_list.append(_d(t.original_amount))
            days_list.append((t.due_date - base).days)
        term = weighted_term_days(amounts=amt_list, days=days_list)
        return {
            "open_amount": open_amount,
            "overdue_amount": overdue,
            "due_in_7_days_amount": due7,
            "due_in_30_days_amount": due30,
            "weighted_term_days": term,
            "partially_paid_count": partial,
            "open_title_count": len(titles),
        }

    async def ap_aging(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], today: date | None = None
    ) -> list[dict[str, Any]]:
        today = today or date.today()
        titles = await self._open_titles(organization_id, station_ids)
        buckets: dict[str, dict[str, Any]] = {
            b.value: {"bucket": b.value, "title_count": 0, "open_amount": _ZERO} for b in AgingBucket
        }
        for t in titles:
            b = aging_bucket(due_date=t.due_date, business_today=today, open_amount=_d(t.open_amount))
            if b is None:
                continue
            buckets[b.value]["title_count"] += 1
            buckets[b.value]["open_amount"] += _d(t.open_amount)
        return list(buckets.values())

    async def list_titles(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = [
            AccountsPayableTitle.organization_id == organization_id,
            AccountsPayableTitle.station_id.in_(station_ids),
        ]
        if status:
            filters.append(AccountsPayableTitle.normalized_status == status)
        total = (
            await self.db.execute(select(func.count()).select_from(AccountsPayableTitle).where(*filters))
        ).scalar_one()
        rows = (
            await self.db.execute(
                select(AccountsPayableTitle)
                .where(*filters)
                .order_by(AccountsPayableTitle.due_date.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        station_names = await self._station_names({r.station_id for r in rows})
        dist_names = await self._distributor_names({r.distributor_id for r in rows if r.distributor_id})
        out = [
            {
                "id": t.id,
                "station_id": t.station_id,
                "station_name": station_names.get(t.station_id, str(t.station_id)),
                "distributor_name": dist_names.get(t.distributor_id) if t.distributor_id else None,
                "document_number": t.document_number,
                "installment_number": t.installment_number,
                "due_date": t.due_date,
                "payment_date": t.payment_date,
                "original_amount": t.original_amount,
                "paid_amount": t.paid_amount,
                "open_amount": t.open_amount,
                "normalized_status": t.normalized_status,
                "purchase_invoice_id": t.purchase_invoice_id,
            }
            for t in rows
        ]
        return out, int(total)

    async def list_nfe(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        page: int,
        page_size: int,
        q: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = [
            NfeXmlDocument.organization_id == organization_id,
            NfeXmlDocument.station_id.in_(station_ids),
        ]
        if q:
            filters.append(
                or_(
                    NfeXmlDocument.access_key.ilike(f"%{q}%"),
                    NfeXmlDocument.document_number.ilike(f"%{q}%"),
                )
            )
        total = (
            await self.db.execute(select(func.count()).select_from(NfeXmlDocument).where(*filters))
        ).scalar_one()
        rows = (
            await self.db.execute(
                select(NfeXmlDocument)
                .where(*filters)
                .order_by(NfeXmlDocument.imported_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        station_names = await self._station_names({r.station_id for r in rows})
        out = [
            {
                "id": d.id,
                "station_id": d.station_id,
                "station_name": station_names.get(d.station_id, str(d.station_id)),
                "access_key": d.access_key,
                "document_number": d.document_number,
                "series": d.series,
                "issuer_cnpj": d.issuer_cnpj,
                "issue_datetime": d.issue_datetime,
                "total_amount": d.total_amount,
                "parse_status": d.parse_status,
                "reconciliation_status": d.reconciliation_status,
                "purchase_invoice_id": d.purchase_invoice_id,
                "xml_size_bytes": d.xml_size_bytes,
            }
            for d in rows
        ]
        return out, int(total)

    async def nfe_detail(
        self, *, organization_id: uuid.UUID, station_ids: list[uuid.UUID], doc_id: uuid.UUID
    ) -> dict[str, Any] | None:
        d = (
            await self.db.execute(
                select(NfeXmlDocument).where(
                    NfeXmlDocument.id == doc_id,
                    NfeXmlDocument.organization_id == organization_id,
                    NfeXmlDocument.station_id.in_(station_ids),
                )
            )
        ).scalar_one_or_none()
        if d is None:
            return None
        station_names = await self._station_names({d.station_id})
        return {
            "id": d.id,
            "station_id": d.station_id,
            "station_name": station_names.get(d.station_id, str(d.station_id)),
            "access_key": d.access_key,
            "document_number": d.document_number,
            "series": d.series,
            "issuer_cnpj": d.issuer_cnpj,
            "recipient_cnpj": d.recipient_cnpj,
            "issue_datetime": d.issue_datetime,
            "total_amount": d.total_amount,
            "parse_status": d.parse_status,
            "reconciliation_status": d.reconciliation_status,
            "purchase_invoice_id": d.purchase_invoice_id,
            "xml_size_bytes": d.xml_size_bytes,
            "parse_errors": d.parse_errors,
            "reconciliation_details": d.reconciliation_details,
            "imported_at": d.imported_at,
        }

    async def _metrics_q(
        self,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[FuelPurchaseDailyMetric]:
        if not station_ids:
            return []
        result = await self.db.execute(
            select(FuelPurchaseDailyMetric).where(
                FuelPurchaseDailyMetric.organization_id == organization_id,
                FuelPurchaseDailyMetric.station_id.in_(station_ids),
                FuelPurchaseDailyMetric.business_date >= date_from,
                FuelPurchaseDailyMetric.business_date <= date_to,
            )
        )
        return list(result.scalars().all())

    async def _open_payable(self, organization_id: uuid.UUID, station_ids: list[uuid.UUID]) -> Decimal:
        titles = await self._open_titles(organization_id, station_ids)
        return sum((_d(t.open_amount) for t in titles), _ZERO)

    async def _open_titles(
        self, organization_id: uuid.UUID, station_ids: list[uuid.UUID]
    ) -> list[AccountsPayableTitle]:
        if not station_ids:
            return []
        result = await self.db.execute(
            select(AccountsPayableTitle).where(
                AccountsPayableTitle.organization_id == organization_id,
                AccountsPayableTitle.station_id.in_(station_ids),
                AccountsPayableTitle.is_cancelled.is_(False),
                AccountsPayableTitle.open_amount > 0,
            )
        )
        return list(result.scalars().all())

    async def _weighted_term(
        self,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> Decimal | None:
        result = await self.db.execute(
            select(AccountsPayableTitle).where(
                AccountsPayableTitle.organization_id == organization_id,
                AccountsPayableTitle.station_id.in_(station_ids),
                AccountsPayableTitle.is_cancelled.is_(False),
                AccountsPayableTitle.issue_date.is_not(None),
                AccountsPayableTitle.issue_date >= date_from,
                AccountsPayableTitle.issue_date <= date_to,
            )
        )
        titles = list(result.scalars().all())
        amounts = [_d(t.original_amount) for t in titles if t.issue_date]
        days = [(t.due_date - t.issue_date).days for t in titles if t.issue_date]
        return weighted_term_days(amounts=amounts, days=days)

    async def _station_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (await self.db.execute(select(Station).where(Station.id.in_(ids)))).scalars().all()
        return {s.id: s.trade_name for s in rows}

    async def _product_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (await self.db.execute(select(Product).where(Product.id.in_(ids)))).scalars().all()
        return {p.id: p.name for p in rows}

    async def _distributor_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (await self.db.execute(select(Distributor).where(Distributor.id.in_(ids)))).scalars().all()
        return {d.id: d.trade_name for d in rows}

    async def _xml_by_invoice(self, invoice_ids: set[uuid.UUID]) -> dict[uuid.UUID, NfeXmlDocument]:
        if not invoice_ids:
            return {}
        rows = (
            await self.db.execute(
                select(NfeXmlDocument).where(NfeXmlDocument.purchase_invoice_id.in_(invoice_ids))
            )
        ).scalars().all()
        return {r.purchase_invoice_id: r for r in rows if r.purchase_invoice_id}

    async def _item_stats_by_invoice(
        self, invoice_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, dict[str, Decimal]]:
        if not invoice_ids:
            return {}
        rows = (
            await self.db.execute(
                select(FuelPurchaseItem).where(FuelPurchaseItem.purchase_invoice_id.in_(invoice_ids))
            )
        ).scalars().all()
        out: dict[uuid.UUID, dict[str, Decimal]] = {}
        for item in rows:
            if item.metric_eligibility_status == PurchaseMetricEligibilityStatus.EXCLUDED.value:
                # Ainda soma volume para listagem operacional; KPIs usam daily metrics.
                pass
            bucket = out.setdefault(item.purchase_invoice_id, {"volume": _ZERO, "delivered": _ZERO})
            if item.volume_liters is not None:
                bucket["volume"] += _d(item.volume_liters)
            bucket["delivered"] += _d(item.commercial_delivered_cost)
        return out
