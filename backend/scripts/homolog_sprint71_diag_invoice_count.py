"""Diagnóstico: 3 vs 4 notas no dia."""

from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource

DAY = "2026-07-09"
DAY_D = date.fromisoformat(DAY)
BRANCH = 2443


async def main() -> None:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
        pg = (
            await db.execute(
                text(
                    """
                    SELECT source_invoice_id, source_document_number, source_series,
                           access_key, total_amount::text, entry_date::text, issue_date::text
                    FROM fuel_purchase_invoices
                    WHERE entry_date = :day
                    ORDER BY source_invoice_id
                    """
                ),
                {"day": DAY_D},
            )
        ).mappings().all()
        print("=== PG ===", len(pg))
        for r in pg:
            print(dict(r))

    ds = DirectSqlServerDataSource(source)
    cur = ds._connect().cursor()  # noqa: SLF001
    cur.execute(
        f"""
        SELECT C.ID_COMPROVANTE, C.NROCOMPROVANTE, C.SAIDAS_ENTRADAS, C.VLRTOTAL,
               C.DTACONTA, C.CANCELADO, C.SERIE
        FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {BRANCH}
          AND C.DTACONTA >= '{DAY}'
          AND C.DTACONTA < DATEADD(day, 1, CAST('{DAY}' AS date))
        ORDER BY C.SAIDAS_ENTRADAS, C.ID_COMPROVANTE
        """
    )
    print("=== ALL SAIDAS day ===")
    for r in cur.fetchall():
        print(r)

    pg_ids = {str(r["source_invoice_id"]) for r in pg}
    cur.execute(
        f"""
        SELECT C.ID_COMPROVANTE, C.NROCOMPROVANTE, C.SAIDAS_ENTRADAS, C.DTACONTA, C.CANCELADO
        FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {BRANCH}
          AND C.ID_COMPROVANTE IN ({",".join(pg_ids) if pg_ids else "0"})
        """
    )
    print("=== PG ids in XPERT now ===")
    for r in cur.fetchall():
        print(r)
    ds.close()


if __name__ == "__main__":
    asyncio.run(main())
