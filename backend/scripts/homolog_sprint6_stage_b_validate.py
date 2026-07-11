"""Validação Etapa B — comparação XPERT vs PostgreSQL por dia."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpSource
from app.models.fuel_sales import FuelSalesFact

DATE_FROM = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 7, 3)
DATE_TO = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 7, 9)
BRANCH = sys.argv[3] if len(sys.argv) > 3 else "2443"


async def pg_by_day() -> dict[str, dict]:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(
                FuelSalesFact.business_date,
                func.count().label("items"),
                func.sum(FuelSalesFact.volume_liters).label("vol"),
                func.sum(FuelSalesFact.net_amount).label("net"),
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
        return {
            str(r.business_date): {"items": r.items, "volume": str(r.vol), "net": str(r.net)}
            for r in rows
        }


async def xpert_by_day() -> dict[str, dict]:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    sql = load_query_file("fuel_sales_items.sql")
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime.combine(DATE_FROM, datetime.min.time(), tzinfo=UTC),
        "window_end": datetime.combine(DATE_TO + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    }
    by_day: dict[str, dict] = {}
    for batch in ds.stream_rows(sql, params, batch_size=10000):
        for row in batch:
            day = str(row.get("source_business_date"))[:10]
            bucket = by_day.setdefault(day, {"items": 0, "volume": Decimal("0"), "net": Decimal("0")})
            bucket["items"] += 1
            bucket["volume"] += Decimal(str(row.get("source_quantity") or 0))
            bucket["net"] += Decimal(str(row.get("source_net_amount") or 0))
    ds.close()
    return {k: {"items": v["items"], "volume": str(v["volume"]), "net": str(v["net"])} for k, v in by_day.items()}


async def main() -> None:
    pg = await pg_by_day()
    xp = await xpert_by_day()
    days = sorted(set(pg) | set(xp))
    lines = []
    for day in days:
        p = pg.get(day, {})
        x = xp.get(day, {})
        lines.append(
            {
                "day": day,
                "xpert_items": x.get("items", 0),
                "pg_eligible_items": p.get("items", 0),
                "item_delta": (x.get("items", 0) or 0) - (p.get("items", 0) or 0),
                "xpert_volume": x.get("volume"),
                "pg_volume": p.get("volume"),
                "xpert_net": x.get("net"),
                "pg_net": p.get("net"),
            }
        )
    print(json.dumps({"from": DATE_FROM.isoformat(), "to": DATE_TO.isoformat(), "days": lines}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
