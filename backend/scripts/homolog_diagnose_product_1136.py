"""Diagnóstico do produto ERP 1136 no XPERT."""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource
from app.models.erp_product import ErpProduct

PRODUCT_ID = "1136"
BRANCH = "2443"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
        local = (
            await db.execute(
                select(ErpProduct).where(ErpProduct.erp_product_id == PRODUCT_ID)
            )
        ).scalars().all()

    ds = DirectSqlServerDataSource(source)
    conn = ds._connect()  # noqa: SLF001
    cur = conn.cursor()

    queries = {
        "by_id_any_branch": """
            SELECT TOP 20
                CAST(ID_PRODUTOS AS VARCHAR(50)) AS id,
                CAST(ID_FILIAL AS VARCHAR(50)) AS filial,
                NOMEPRODUTO AS nome,
                ATIVO AS ativo
            FROM PRODUTOS
            WHERE ID_PRODUTOS = ?
        """,
        "by_id_branch_2443": """
            SELECT
                CAST(ID_PRODUTOS AS VARCHAR(50)) AS id,
                CAST(ID_FILIAL AS VARCHAR(50)) AS filial,
                NOMEPRODUTO AS nome,
                ATIVO AS ativo
            FROM PRODUTOS
            WHERE ID_PRODUTOS = ? AND ID_FILIAL = ?
        """,
        "sale_item_product": """
            SELECT TOP 5
                CAST(I.ID_ITENSMOVPRODUTOS AS VARCHAR(50)) AS item_id,
                CAST(I.ID_PRODUTOS AS VARCHAR(50)) AS product_id,
                CAST(I.ID_FILIAL AS VARCHAR(50)) AS filial,
                CAST(I.ID_DB AS VARCHAR(50)) AS id_db,
                CAST(I.CFOP AS VARCHAR(20)) AS cfop,
                I.QTDE AS qtde,
                I.TOTAL AS total
            FROM ITENSMOVPRODUTOS I
            WHERE I.ID_ITENSMOVPRODUTOS = 2150248
        """,
        "products_query_active_only_count": """
            SELECT COUNT(*) AS c
            FROM PRODUTOS
            WHERE ID_FILIAL = ? AND ATIVO = 1 AND ID_PRODUTOS = ?
        """,
        "products_query_including_inactive": """
            SELECT COUNT(*) AS c
            FROM PRODUTOS
            WHERE ID_FILIAL = ? AND ID_PRODUTOS = ?
        """,
    }

    result: dict = {
        "local_erp_products": [
            {
                "id": str(p.id),
                "station_id": str(p.station_id),
                "description": p.erp_description,
                "active": p.active,
                "source_active": p.source_active,
                "mapping_status": p.mapping_status,
            }
            for p in local
        ],
        "xpert": {},
    }

    cur.execute(queries["by_id_any_branch"], (int(PRODUCT_ID),))
    cols = [d[0] for d in cur.description]
    result["xpert"]["by_id_any_branch"] = [dict(zip(cols, row)) for row in cur.fetchall()]

    cur.execute(queries["by_id_branch_2443"], (int(PRODUCT_ID), BRANCH))
    cols = [d[0] for d in cur.description]
    result["xpert"]["by_id_branch_2443"] = [dict(zip(cols, row)) for row in cur.fetchall()]

    cur.execute(queries["sale_item_product"])
    cols = [d[0] for d in cur.description]
    result["xpert"]["sale_item"] = [dict(zip(cols, row)) for row in cur.fetchall()]

    cur.execute(queries["products_query_active_only_count"], (BRANCH, int(PRODUCT_ID)))
    result["xpert"]["active_only_count"] = cur.fetchone()[0]

    cur.execute(queries["products_query_including_inactive"], (BRANCH, int(PRODUCT_ID)))
    result["xpert"]["including_inactive_count"] = cur.fetchone()[0]

    # Check if ATIVO filter is the cause
    if result["xpert"]["by_id_branch_2443"]:
        row = result["xpert"]["by_id_branch_2443"][0]
        result["diagnosis"] = {
            "exists_in_branch": True,
            "ativo": bool(row.get("ativo")),
            "omitted_by_products_query_ativo_filter": not bool(row.get("ativo")),
            "scenario": "A_INACTIVE_OMITTED_BY_QUERY" if not bool(row.get("ativo")) else "A_ACTIVE_BUT_NOT_SYNCED",
        }
    elif result["xpert"]["by_id_any_branch"]:
        result["diagnosis"] = {
            "exists_in_branch": False,
            "exists_other_branch": True,
            "other_branches": result["xpert"]["by_id_any_branch"],
            "scenario": "A_OTHER_BRANCH_OR_ID_DB",
        }
    else:
        result["diagnosis"] = {
            "exists_in_branch": False,
            "exists_anywhere": False,
            "scenario": "B_HISTORICAL_ORPHAN",
        }

    cur.close()
    ds.close()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
