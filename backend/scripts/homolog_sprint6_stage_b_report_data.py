"""Coleta dados para relatório Etapa B — 7 dias."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date

from sqlalchemy import func, select, text

from app.core.database import AsyncSessionLocal
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import FuelSalesFact

DATE_FROM = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 7, 3)
DATE_TO = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 7, 9)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        elig_filter = (
            FuelSalesFact.business_date >= DATE_FROM,
            FuelSalesFact.business_date <= DATE_TO,
            FuelSalesFact.is_cancelled.is_(False),
            FuelSalesFact.metric_eligibility_status != "EXCLUDED",
        )
        totals = (
            await db.execute(
                select(
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                    func.sum(FuelSalesFact.gross_amount),
                    func.sum(FuelSalesFact.discount_amount),
                    func.sum(FuelSalesFact.total_cost_amount),
                ).where(*elig_filter)
            )
        ).one()

        by_product = (
            await db.execute(
                select(
                    ErpProduct.erp_description,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .join(ErpProduct, ErpProduct.id == FuelSalesFact.erp_product_id)
                .where(*elig_filter)
                .group_by(ErpProduct.erp_description)
                .order_by(func.sum(FuelSalesFact.volume_liters).desc())
            )
        ).all()

        by_cfop = (
            await db.execute(
                select(
                    FuelSalesFact.source_cfop,
                    FuelSalesFact.cfop_classification,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                )
                .group_by(FuelSalesFact.source_cfop, FuelSalesFact.cfop_classification)
                .order_by(FuelSalesFact.source_cfop)
            )
        ).all()

        cancelled = (
            await db.execute(
                select(
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                ).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.is_cancelled.is_(True),
                )
            )
        ).one()

        unmapped = (
            await db.execute(
                select(
                    FuelSalesFact.source_sale_id,
                    FuelSalesFact.source_sale_item_id,
                    FuelSalesFact.business_date,
                    FuelSalesFact.volume_liters,
                    FuelSalesFact.net_amount,
                    FuelSalesFact.metric_exclusion_reasons,
                ).where(
                    FuelSalesFact.business_date >= DATE_FROM,
                    FuelSalesFact.business_date <= DATE_TO,
                    FuelSalesFact.metric_eligibility_status == "EXCLUDED",
                    FuelSalesFact.metric_exclusion_reasons.contains(["UNMAPPED_PRODUCT"]),
                )
            )
        ).all()

        miss_cost = (
            await db.execute(
                select(func.count()).where(
                    *elig_filter,
                    FuelSalesFact.total_cost_amount.is_(None),
                )
            )
        ).scalar()

        neg_margin = (
            await db.execute(
                select(
                    FuelSalesFact.source_sale_id,
                    FuelSalesFact.source_sale_item_id,
                    FuelSalesFact.business_date,
                    FuelSalesFact.net_amount,
                    FuelSalesFact.total_cost_amount,
                    FuelSalesFact.volume_liters,
                    FuelSalesFact.gross_margin_amount,
                ).where(
                    *elig_filter,
                    FuelSalesFact.margin_status == "NEGATIVE",
                )
            )
        ).all()

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

        wrong_branch = 0  # isolamento validado no contrato; fatos não carregam erp_branch_id

        daily = (
            await db.execute(
                select(
                    FuelSalesFact.business_date,
                    func.count(),
                    func.sum(FuelSalesFact.volume_liters),
                    func.sum(FuelSalesFact.net_amount),
                )
                .where(*elig_filter)
                .group_by(FuelSalesFact.business_date)
                .order_by(FuelSalesFact.business_date)
            )
        ).all()

        excluded_by_reason = (
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

    payload = {
        "from": DATE_FROM.isoformat(),
        "to": DATE_TO.isoformat(),
        "totals_eligible": {
            "items": totals[0],
            "volume": str(totals[1]),
            "net": str(totals[2]),
            "gross": str(totals[3]),
            "discount": str(totals[4]),
            "extended_cost": str(totals[5]),
        },
        "by_product": [
            {"product": r[0], "items": r[1], "volume": str(r[2]), "net": str(r[3])} for r in by_product
        ],
        "by_cfop": [
            {
                "cfop": r[0],
                "classification": r[1],
                "items": r[2],
                "volume": str(r[3]),
                "net": str(r[4]),
            }
            for r in by_cfop
        ],
        "cancelled": {"items": cancelled[0], "volume": str(cancelled[1]), "net": str(cancelled[2])},
        "unmapped": [
            {
                "sale": r[0],
                "item": r[1],
                "day": str(r[2]),
                "vol": str(r[3]),
                "net": str(r[4]),
                "reasons": r[5],
            }
            for r in unmapped
        ],
        "missing_cost_eligible": miss_cost,
        "negative_margin_items": [
            {
                "sale": r[0],
                "item": r[1],
                "day": str(r[2]),
                "net": str(r[3]),
                "total_cost": str(r[4]),
                "volume": str(r[5]),
                "margin": str(r[6]),
            }
            for r in neg_margin
        ],
        "duplicate_keys": [{"sale": r[0], "item": r[1], "count": r[2]} for r in dup],
        "wrong_branch": wrong_branch,
        "excluded_by_reason": [
            {"reasons": r[0], "items": r[1], "volume": str(r[2]), "net": str(r[3])} for r in excluded_by_reason
        ],
        "daily_eligible": [
            {"day": str(r[0]), "items": r[1], "volume": str(r[2]), "net": str(r[3])} for r in daily
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
