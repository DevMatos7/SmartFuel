"""Comparação contábil 1 dia — PostgreSQL vs XPERT direto."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select, text

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpSource
from app.models.fuel_sales import FuelSalesFact

SALES_DAY = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 7, 9)
BRANCH = sys.argv[2] if len(sys.argv) > 2 else "2443"


async def postgres_stats() -> dict:
    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                select(
                    func.count().label("items"),
                    func.sum(FuelSalesFact.volume_liters).label("vol"),
                    func.sum(FuelSalesFact.net_amount).label("net"),
                    func.sum(FuelSalesFact.gross_amount).label("gross"),
                    func.sum(FuelSalesFact.discount_amount).label("disc"),
                    func.sum(FuelSalesFact.total_cost_amount).label("cost"),
                ).where(
                    FuelSalesFact.business_date == SALES_DAY,
                    FuelSalesFact.is_cancelled.is_(False),
                    FuelSalesFact.metric_eligibility_status != "EXCLUDED",
                )
            )
        ).one()
        cancelled = await db.scalar(
            select(func.count()).select_from(FuelSalesFact).where(
                FuelSalesFact.business_date == SALES_DAY,
                FuelSalesFact.is_cancelled.is_(True),
            )
        )
        returns = await db.scalar(
            select(func.count()).select_from(FuelSalesFact).where(
                FuelSalesFact.business_date == SALES_DAY,
                FuelSalesFact.operation_type == "RETURN",
            )
        )
        dup = await db.scalar(
            text(
                """
                SELECT COUNT(*) FROM (
                  SELECT source_sale_id, source_sale_item_id, COUNT(*) c
                  FROM fuel_sales_facts WHERE business_date=:d
                  GROUP BY 1,2 HAVING COUNT(*)>1
                ) t
                """
            ),
            {"d": SALES_DAY},
        )
        return {
            "eligible_items": row.items,
            "volume_liters": str(row.vol),
            "net_amount": str(row.net),
            "gross_amount": str(row.gross),
            "discount_amount": str(row.disc),
            "cost_amount": str(row.cost),
            "cancelled_items": cancelled,
            "return_items": returns,
            "duplicate_natural_keys": dup,
        }


async def xpert_stats() -> dict:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    cfop_sql = f"""
        SELECT I.CFOP,
               COUNT(*) AS items,
               SUM(CAST(ROUND(I.QTDE,6) AS DECIMAL(18,6))) AS volume,
               SUM(CAST(ROUND(I.TOTAL,4) AS DECIMAL(20,4))) AS net
        FROM ITENSMOVPRODUTOS I
        INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
        INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
        WHERE I.ID_FILIAL=? AND M.ID_FILIAL=? AND C.ID_FILIAL=?
          AND C.SAIDAS_ENTRADAS=0 AND I.CFOP > '3000'
          AND CONVERT(DATE, M.DATA)=?
        GROUP BY I.CFOP ORDER BY items DESC
    """
    conn = ds._connect()
    cursor = conn.cursor()
    cursor.execute(cfop_sql, (BRANCH, BRANCH, BRANCH, SALES_DAY.isoformat()))
    cfop_rows = [
        {"cfop": r[0], "items": r[1], "volume": str(r[2]), "net": str(r[3])}
        for r in cursor.fetchall()
    ]

    query_sql = load_query_file("fuel_sales_items.sql")
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime.combine(SALES_DAY, datetime.min.time(), tzinfo=UTC),
        "window_end": datetime.combine(SALES_DAY + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
    }
    items = 0
    volume = 0.0
    net = 0.0
    branches: set[str] = set()
    keys: set[tuple[str, str]] = set()
    dup_keys: list[str] = []
    for batch in ds.stream_rows(query_sql, params, batch_size=5000):
        for row in batch:
            key = (str(row["source_sale_id"]), str(row["source_sale_item_id"]))
            if key in keys:
                dup_keys.append(f"{key[0]}:{key[1]}")
            keys.add(key)
            items += 1
            volume += float(row.get("source_quantity") or 0)
            net += float(row.get("source_net_amount") or 0)
            if row.get("source_branch_id") is not None:
                branches.add(str(row["source_branch_id"]))
    ds.close()
    return {
        "cfop_breakdown": cfop_rows,
        "contract_items": items,
        "contract_volume": volume,
        "contract_net": net,
        "distinct_branches": sorted(branches),
        "duplicate_keys_in_query": dup_keys[:10],
        "duplicate_key_count": len(dup_keys),
    }


async def main() -> None:
    pg = await postgres_stats()
    xp = await xpert_stats()
    print(json.dumps({"sales_day": SALES_DAY.isoformat(), "branch": BRANCH, "postgres": pg, "xpert": xp}, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
