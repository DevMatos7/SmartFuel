"""Validação Etapa C — 30 dias: isolamento, CFOP, exclusões, agregações."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text

from app.core.cfop_policy import get_cfop_policy, normalize_cfop
from app.core.database import AsyncSessionLocal
from app.core.fuel_sales_normalization import (
    FUEL_SALES_CFOP_POLICY_VERSION,
    FUEL_SALES_HASH_SCHEMA_VERSION,
    FUEL_SALES_NORMALIZATION_VERSION,
)
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncCheckpoint, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import FuelSalesDailyMetric, FuelSalesFact
from app.models.product import Product

DATE_FROM = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 6, 10)
DATE_TO = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 7, 9)
BRANCH = sys.argv[3] if len(sys.argv) > 3 else "2443"
OUT = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("docs/sprints/sprint-06-etapa-c-validate.json")


def _d(v) -> str | None:
    return None if v is None else str(v)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        total_facts = (
            await db.execute(
                select(func.count()).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                )
            )
        ).scalar()

        dup = (
            await db.execute(
                text(
                    """
                    SELECT source_sale_id, source_sale_item_id, count(*) c
                    FROM fuel_sales_facts
                    WHERE business_date BETWEEN :f AND :t
                    GROUP BY source_sale_id, source_sale_item_id
                    HAVING count(*) > 1
                    """
                ),
                {"f": DATE_FROM, "t": DATE_TO},
            )
        ).all()

        by_cfop = (
            await db.execute(
                select(
                    FuelSalesFact.source_cfop,
                    FuelSalesFact.cfop_classification,
                    FuelSalesFact.is_cancelled,
                    FuelSalesFact.metric_eligibility_status,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                )
                .group_by(
                    FuelSalesFact.source_cfop,
                    FuelSalesFact.cfop_classification,
                    FuelSalesFact.is_cancelled,
                    FuelSalesFact.metric_eligibility_status,
                )
            )
        ).all()

        excluded = (
            await db.execute(
                select(
                    FuelSalesFact.metric_exclusion_reasons,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.metric_eligibility_status == "EXCLUDED",
                )
                .group_by(FuelSalesFact.metric_exclusion_reasons)
            )
        ).all()

        eligible = (
            await db.execute(
                select(
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.gross_amount),
                    func.sum(FuelSalesFact.discount_amount),
                    func.sum(FuelSalesFact.net_amount),
                    func.sum(FuelSalesFact.total_cost_amount),
                    func.sum(FuelSalesFact.gross_margin_amount),
                ).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.is_cancelled.is_(False),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
            )
        ).one()

        by_unit = (
            await db.execute(
                select(
                    FuelSalesFact.source_unit,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                )
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                )
                .group_by(FuelSalesFact.source_unit)
            )
        ).all()

        product_1507 = (
            await db.execute(
                select(
                    FuelSalesFact.metric_eligibility_status,
                    FuelSalesFact.metric_exclusion_reasons,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .join(ErpProduct, ErpProduct.id == FuelSalesFact.erp_product_id)
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    ErpProduct.erp_product_id == "1507",
                )
                .group_by(
                    FuelSalesFact.metric_eligibility_status,
                    FuelSalesFact.metric_exclusion_reasons,
                )
            )
        ).all()

        fuel_kpi_5102 = (
            await db.execute(
                select(func.count()).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.source_cfop.in_(["5.102", "5102"]),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
            )
        ).scalar()

        fuel_kpi_5405 = (
            await db.execute(
                select(func.count()).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.source_cfop.in_(["5.405", "5405"]),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
            )
        ).scalar()

        missing_cost_as_zero = (
            await db.execute(
                select(func.count()).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                    FuelSalesFact.total_cost_amount == 0,
                    FuelSalesFact.cost_per_liter.is_(None),
                )
            )
        ).scalar()

        neg_margin = (
            await db.execute(
                select(func.count()).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                    FuelSalesFact.margin_status == "NEGATIVE",
                )
            )
        ).scalar()

        facts_daily = (
            await db.execute(
                select(
                    FuelSalesFact.business_date,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.is_cancelled.is_(False),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
                .group_by(FuelSalesFact.business_date)
                .order_by(FuelSalesFact.business_date)
            )
        ).all()

        agg_daily = (
            await db.execute(
                select(
                    FuelSalesDailyMetric.business_date,
                    func.sum(FuelSalesDailyMetric.sales_item_count),
                    func.sum(FuelSalesDailyMetric.net_volume_liters),
                    func.sum(FuelSalesDailyMetric.net_sales_amount),
                )
                .where(
                    FuelSalesDailyMetric.business_date >= DATE_FROM,
                    FuelSalesDailyMetric.business_date <= DATE_TO,
                )
                .group_by(FuelSalesDailyMetric.business_date)
                .order_by(FuelSalesDailyMetric.business_date)
            )
        ).all()

        agg_map = {r[0]: r for r in agg_daily}
        agg_matches = []
        for day, items, vol, net in facts_daily:
            a = agg_map.get(day)
            match = a is not None and a[1] == items and a[2] == vol and a[3] == net
            agg_matches.append(
                {
                    "day": str(day),
                    "facts_items": items,
                    "agg_items": None if a is None else int(a[1]),
                    "match": match,
                }
            )

        by_product = (
            await db.execute(
                select(
                    Product.name,
                    Product.fuel_family,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .join(Product, Product.id == FuelSalesFact.canonical_product_id)
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.is_cancelled.is_(False),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
                .group_by(Product.name, Product.fuel_family)
                .order_by(func.sum(FuelSalesFact.volume_liters).desc())
            )
        ).all()

        ds = (
            await db.execute(select(ErpDataset).where(ErpDataset.code == "FUEL_SALES_ITEMS"))
        ).scalar_one()
        cps = (
            await db.execute(
                select(ErpSyncCheckpoint).where(ErpSyncCheckpoint.erp_dataset_id == ds.id)
            )
        ).scalars().all()
        last_runs = (
            await db.execute(
                select(ErpSyncRun)
                .where(ErpSyncRun.erp_dataset_id == ds.id)
                .order_by(ErpSyncRun.created_at.desc())
                .limit(3)
            )
        ).scalars().all()

        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()

    # XPERT read-only profile by CFOP
    xpert_ds = DirectSqlServerDataSource(source)
    sql = load_query_file("fuel_sales_items.sql")
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime.combine(DATE_FROM, datetime.min.time(), tzinfo=UTC),
        "window_end": datetime.combine(DATE_TO + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    }
    xpert_cfop: dict[str, dict] = {}
    foreign_branch = 0
    xpert_total = 0
    for batch in xpert_ds.stream_rows(sql, params, batch_size=10000):
        for row in batch:
            xpert_total += 1
            if str(row.get("source_branch_id")) != BRANCH:
                foreign_branch += 1
            cfop = normalize_cfop(row.get("source_cfop")) or "NULL"
            b = xpert_cfop.setdefault(
                cfop,
                {
                    "items_total": 0,
                    "items_active": 0,
                    "items_cancelled": 0,
                    "volume": Decimal("0"),
                    "net": Decimal("0"),
                },
            )
            b["items_total"] += 1
            qty = Decimal(str(row.get("source_quantity") or 0))
            net = Decimal(str(row.get("source_net_amount") or 0))
            b["volume"] += qty
            b["net"] += net
            if row.get("source_cancelled"):
                b["items_cancelled"] += 1
            else:
                b["items_active"] += 1
    xpert_ds.close()

    payload = {
        "from": DATE_FROM.isoformat(),
        "to": DATE_TO.isoformat(),
        "versions": {
            "normalization_version": FUEL_SALES_NORMALIZATION_VERSION,
            "hash_schema_version": FUEL_SALES_HASH_SCHEMA_VERSION,
            "cfop_policy_version": FUEL_SALES_CFOP_POLICY_VERSION,
            "query_hash": ds.query_hash,
        },
        "isolation": {
            "foreign_branch_rows": foreign_branch,
            "xpert_total_rows": xpert_total,
            "postgres_total_facts": total_facts,
            "duplicate_natural_keys": [{"sale": r[0], "item": r[1], "count": r[2]} for r in dup],
        },
        "checkpoints": [
            {
                "station_id": str(c.station_id),
                "watermark_value": c.watermark_value,
                "source_upper_bound": c.source_upper_bound,
                "last_success_at": _d(c.last_success_at),
            }
            for c in cps
        ],
        "recent_runs": [
            {
                "id": str(r.id),
                "status": r.status,
                "rows_read": r.rows_read,
                "rows_inserted": r.rows_inserted,
                "rows_updated": r.rows_updated,
                "rows_unchanged": r.rows_unchanged,
                "rows_error": r.rows_error,
                "checkpoint_before": r.checkpoint_before,
                "checkpoint_after": r.checkpoint_after,
                "normalization_version": r.normalization_version,
                "hash_schema_version": r.hash_schema_version,
                "window_start": _d(r.window_start),
                "window_end": _d(r.window_end),
                "created_at": _d(r.created_at),
            }
            for r in last_runs
        ],
        "xpert_by_cfop": {
            k: {
                **{kk: (str(vv) if isinstance(vv, Decimal) else vv) for kk, vv in v.items()},
                "policy": get_cfop_policy(None if k == "NULL" else k).treatment.value,
                "analytics_scope": get_cfop_policy(None if k == "NULL" else k).default_analytics_scope,
            }
            for k, v in sorted(xpert_cfop.items())
        },
        "postgres_by_cfop": [
            {
                "cfop": r[0],
                "classification": r[1],
                "cancelled": r[2],
                "eligibility": r[3],
                "items": r[4],
                "volume": _d(r[5]),
                "net": _d(r[6]),
            }
            for r in by_cfop
        ],
        "excluded_by_reason": [
            {
                "reasons": r[0],
                "items": r[1],
                "volume": _d(r[2]),
                "net": _d(r[3]),
            }
            for r in excluded
        ],
        "eligible_totals": {
            "items": eligible[0],
            "volume": _d(eligible[1]),
            "gross": _d(eligible[2]),
            "discount": _d(eligible[3]),
            "net": _d(eligible[4]),
            "cost": _d(eligible[5]),
            "margin": _d(eligible[6]),
        },
        "by_unit": [{"unit": r[0], "items": r[1], "volume": _d(r[2])} for r in by_unit],
        "by_product_eligible": [
            {
                "product": r[0],
                "fuel_family": r[1],
                "items": r[2],
                "volume": _d(r[3]),
                "net": _d(r[4]),
            }
            for r in by_product
        ],
        "gates": {
            "cfop_5102_in_fuel_kpi": fuel_kpi_5102,
            "cfop_5405_in_fuel_kpi": fuel_kpi_5405,
            "product_1507": [
                {
                    "eligibility": r[0],
                    "reasons": r[1],
                    "items": r[2],
                    "volume": _d(r[3]),
                    "net": _d(r[4]),
                }
                for r in product_1507
            ],
            "missing_cost_as_zero": missing_cost_as_zero,
            "negative_margin_items": neg_margin,
            "aggregation_days_matched": sum(1 for x in agg_matches if x["match"]),
            "aggregation_days_total": len(agg_matches),
            "aggregation_detail": agg_matches,
        },
    }
    text_out = json.dumps(payload, indent=2, ensure_ascii=False)
    print(text_out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text_out, encoding="utf-8")
    print(f"Salvo: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
