"""Perfil read-only de CFOPs — 30 dias (sem aplicação no domínio)."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.cfop_policy import get_cfop_policy, normalize_cfop
from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpSource

DATE_FROM = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 6, 10)
DATE_TO = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2026, 7, 9)
BRANCH = sys.argv[3] if len(sys.argv) > 3 else "2443"
OUT = sys.argv[4] if len(sys.argv) > 4 else "docs/sprints/sprint-06-cfop-profile-30d.json"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    sql = load_query_file("fuel_sales_items.sql")
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime.combine(DATE_FROM, datetime.min.time(), tzinfo=UTC),
        "window_end": datetime.combine(DATE_TO + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    }

    by_cfop: dict[str, dict] = {}
    for batch in ds.stream_rows(sql, params, batch_size=10000):
        for row in batch:
            cfop = normalize_cfop(row.get("source_cfop")) or "NULL"
            policy = get_cfop_policy(None if cfop == "NULL" else cfop)
            bucket = by_cfop.setdefault(
                cfop,
                {
                    "cfop": cfop,
                    "policy": policy.treatment.value,
                    "operation_class": policy.operation_class,
                    "fiscal_category": policy.fiscal_category,
                    "analytics_scope": policy.default_analytics_scope,
                    "review_status": policy.review_status,
                    "items_total": 0,
                    "items_cancelled": 0,
                    "items_active": 0,
                    "volume_total": Decimal("0"),
                    "volume_active": Decimal("0"),
                    "net_total": Decimal("0"),
                    "net_active": Decimal("0"),
                    "products": set(),
                    "first_day": None,
                    "last_day": None,
                    "days": set(),
                },
            )
            cancelled = bool(row.get("source_cancelled"))
            qty = Decimal(str(row.get("source_quantity") or 0))
            net = Decimal(str(row.get("source_net_amount") or 0))
            day = str(row.get("source_business_date"))[:10]
            product = str(row.get("source_product_id"))

            bucket["items_total"] += 1
            bucket["volume_total"] += qty
            bucket["net_total"] += net
            bucket["products"].add(product)
            bucket["days"].add(day)
            if bucket["first_day"] is None or day < bucket["first_day"]:
                bucket["first_day"] = day
            if bucket["last_day"] is None or day > bucket["last_day"]:
                bucket["last_day"] = day
            if cancelled:
                bucket["items_cancelled"] += 1
            else:
                bucket["items_active"] += 1
                bucket["volume_active"] += qty
                bucket["net_active"] += net

    ds.close()

    rows = []
    for cfop in sorted(by_cfop, key=lambda k: (k == "NULL", k)):
        b = by_cfop[cfop]
        rows.append(
            {
                "cfop": b["cfop"],
                "policy": b["policy"],
                "operation_class": b["operation_class"],
                "fiscal_category": b["fiscal_category"],
                "analytics_scope": b["analytics_scope"],
                "review_status": b["review_status"],
                "items_total": b["items_total"],
                "items_cancelled": b["items_cancelled"],
                "items_active": b["items_active"],
                "volume_total": str(b["volume_total"]),
                "volume_active": str(b["volume_active"]),
                "net_total": str(b["net_total"]),
                "net_active": str(b["net_active"]),
                "product_count": len(b["products"]),
                "products_sample": sorted(b["products"])[:10],
                "first_day": b["first_day"],
                "last_day": b["last_day"],
                "day_count": len(b["days"]),
            }
        )

    payload = {
        "mode": "READ_ONLY",
        "branch": BRANCH,
        "from": DATE_FROM.isoformat(),
        "to": DATE_TO.isoformat(),
        "total_cfops": len(rows),
        "pending_review_active_items": sum(
            r["items_active"] for r in rows if r["policy"] == "PENDING_REVIEW"
        ),
        "non_fuel_by_default_active_items": sum(
            r["items_active"] for r in rows if r["analytics_scope"] == "NON_FUEL_BY_DEFAULT"
        ),
        "cfops": rows,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    print(text)
    if OUT:
        from pathlib import Path

        path = Path(OUT)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Salvo em: {path}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
