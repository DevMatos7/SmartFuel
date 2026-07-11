"""Reconciliação linha a linha — dia único XPERT vs PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.cfop_policy import classify_cfop, normalize_cfop
from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpSource
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import FuelSalesFact

SALES_DAY = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 7, 9)
BRANCH = sys.argv[2] if len(sys.argv) > 2 else "2443"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("docs/sprints/sprint-06-dia-reconciliacao-0907.json")


def _key(sale_id: str, item_id: str) -> str:
    return f"{sale_id}:{item_id}"


async def load_postgres_rows() -> dict[str, dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FuelSalesFact).where(FuelSalesFact.business_date == SALES_DAY))
        facts = list(result.scalars().all())
        # reload erp products
        erp_ids = {f.erp_product_id for f in facts}
        erp_map: dict = {}
        if erp_ids:
            erps = await db.execute(select(ErpProduct).where(ErpProduct.id.in_(erp_ids)))
            erp_map = {e.id: e for e in erps.scalars().all()}

    rows: dict[str, dict] = {}
    for fact in facts:
        erp = erp_map.get(fact.erp_product_id)
        rows[_key(fact.source_sale_id, fact.source_sale_item_id)] = {
            "source_sale_id": fact.source_sale_id,
            "source_sale_item_id": fact.source_sale_item_id,
            "cfop": fact.source_cfop,
            "cfop_classification": fact.cfop_classification,
            "cancelled": fact.is_cancelled,
            "mapping_status": erp.mapping_status if erp else None,
            "erp_description": erp.erp_description if erp else None,
            "volume": str(fact.volume_liters),
            "net_amount": str(fact.net_amount),
            "metric_eligibility_status": fact.metric_eligibility_status,
            "metric_exclusion_reasons": fact.metric_exclusion_reasons,
            "in_postgres": True,
        }
    return rows


async def load_xpert_rows() -> dict[str, dict]:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    sql = load_query_file("fuel_sales_items.sql")
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime.combine(SALES_DAY, datetime.min.time(), tzinfo=UTC),
        "window_end": datetime.combine(SALES_DAY + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    }
    rows: dict[str, dict] = {}
    for batch in ds.stream_rows(sql, params, batch_size=5000):
        for row in batch:
            sale_id = str(row["source_sale_id"])
            item_id = str(row["source_sale_item_id"])
            cfop = row.get("source_cfop")
            rows[_key(sale_id, item_id)] = {
                "source_sale_id": sale_id,
                "source_sale_item_id": item_id,
                "cfop": str(cfop) if cfop is not None else None,
                "cfop_normalized": normalize_cfop(str(cfop) if cfop is not None else None),
                "cfop_policy": classify_cfop(str(cfop) if cfop is not None else None).value,
                "cancelled": bool(row.get("source_cancelled")),
                "volume": str(row.get("source_quantity")),
                "net_amount": str(row.get("source_net_amount")),
                "in_xpert": True,
            }
    ds.close()
    return rows


async def main() -> None:
    pg = await load_postgres_rows()
    xp = await load_xpert_rows()
    all_keys = sorted(set(pg) | set(xp))

    lines: list[dict] = []
    summary = {
        "xpert_total": len(xp),
        "postgres_total": len(pg),
        "eligible": 0,
        "cancelled": 0,
        "unmapped": 0,
        "pending_cfop": 0,
        "only_xpert": 0,
        "only_postgres": 0,
        "volume_xpert": Decimal("0"),
        "volume_pg_eligible": Decimal("0"),
        "net_xpert": Decimal("0"),
        "net_pg_eligible": Decimal("0"),
    }

    for key in all_keys:
        x = xp.get(key, {})
        p = pg.get(key, {})
        merged = {
            "key": key,
            "source_sale_id": x.get("source_sale_id") or p.get("source_sale_id"),
            "source_sale_item_id": x.get("source_sale_item_id") or p.get("source_sale_item_id"),
            "cfop": x.get("cfop") or p.get("cfop"),
            "cfop_policy": x.get("cfop_policy") or p.get("cfop_classification"),
            "cancelled": x.get("cancelled", p.get("cancelled")),
            "mapping_status": p.get("mapping_status"),
            "volume_xpert": x.get("volume"),
            "volume_postgres": p.get("volume"),
            "net_xpert": x.get("net_amount"),
            "net_postgres": p.get("net_amount"),
            "metric_eligibility_status": p.get("metric_eligibility_status"),
            "metric_exclusion_reasons": p.get("metric_exclusion_reasons"),
            "in_xpert": key in xp,
            "in_postgres": key in pg,
        }
        reasons = p.get("metric_exclusion_reasons") or []
        if merged["cancelled"]:
            merged["exclusion_category"] = "CANCELLED"
            summary["cancelled"] += 1
        elif "UNMAPPED_PRODUCT" in reasons:
            merged["exclusion_category"] = "UNMAPPED"
            summary["unmapped"] += 1
        elif "PENDING_CFOP_CLASSIFICATION" in reasons:
            merged["exclusion_category"] = "PENDING_CFOP"
            summary["pending_cfop"] += 1
        elif p.get("metric_eligibility_status") == "ELIGIBLE" or p.get("metric_eligibility_status") == "ELIGIBLE_WITH_WARNINGS":
            merged["exclusion_category"] = "ELIGIBLE"
            summary["eligible"] += 1
            summary["volume_pg_eligible"] += Decimal(p.get("volume") or "0")
            summary["net_pg_eligible"] += Decimal(p.get("net_amount") or "0")
        elif key in pg:
            merged["exclusion_category"] = "OTHER_EXCLUDED"
        else:
            merged["exclusion_category"] = "MISSING_IN_POSTGRES"
            summary["only_xpert"] += 1

        if key in xp:
            summary["volume_xpert"] += Decimal(x.get("volume") or "0")
            summary["net_xpert"] += Decimal(x.get("net_amount") or "0")
        if key in pg and key not in xp:
            summary["only_postgres"] += 1

        lines.append(merged)

    payload = {
        "sales_day": SALES_DAY.isoformat(),
        "branch": BRANCH,
        "summary": {k: str(v) if isinstance(v, Decimal) else v for k, v in summary.items()},
        "reconciliation_formula": (
            f"{summary['xpert_total']} XPERT = {summary['eligible']} elegíveis + "
            f"{summary['cancelled']} cancelados + {summary['unmapped']} não mapeados + "
            f"{summary['pending_cfop']} CFOP pendente + outros"
        ),
        "lines": lines,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Detalhe salvo em {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
