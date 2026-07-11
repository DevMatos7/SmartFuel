"""Probe COMPENTRADAS — chave NF-e e frete."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource


async def main() -> None:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    cur = ds._connect().cursor()  # noqa: SLF001
    try:
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'COMPENTRADAS' ORDER BY ORDINAL_POSITION"
        )
        print("=== COMPENTRADAS columns ===")
        for r in cur.fetchall():
            print(f"  {r[0]}: {r[1]}")

        cur.execute(
            """
            SELECT TOP 10
                CE.ID_COMPENTRADAS, CE.ID_FILIAL, CE.ID_COMPROVANTE,
                CE.VLRFRETE, CE.VLRSEGURO, CE.VLROUTROS,
                CE.CHAVEACESSONFE, CE.IMPORTOU_XML, CE.CONFERIDA
            FROM COMPENTRADAS CE
            WHERE CE.ID_FILIAL = 2443
              AND CE.CHAVEACESSONFE IS NOT NULL
              AND LEN(LTRIM(RTRIM(CE.CHAVEACESSONFE))) = 44
            ORDER BY CE.ID_COMPENTRADAS DESC
            """
        )
        print("=== SAMPLE 2443 with key ===")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            print(dict(zip(cols, row, strict=False)))

        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN CE.CHAVEACESSONFE IS NOT NULL AND LEN(LTRIM(RTRIM(CE.CHAVEACESSONFE))) = 44 THEN 1 ELSE 0 END) AS com_chave,
                SUM(CASE WHEN ISNULL(CE.VLRFRETE,0) > 0 THEN 1 ELSE 0 END) AS com_frete,
                SUM(CASE WHEN CE.IMPORTOU_XML = 1 THEN 1 ELSE 0 END) AS importou_xml_flag
            FROM COMPENTRADAS CE
            INNER JOIN COMPROVANTES C
              ON C.ID_COMPROVANTE = CE.ID_COMPROVANTE
             AND C.ID_FILIAL = CE.ID_FILIAL
             AND C.ID_DB = CE.ID_DB
            WHERE CE.ID_FILIAL = 2443
              AND C.DTACONTA >= '2026-07-09'
              AND C.DTACONTA < '2026-07-10'
              AND C.SAIDAS_ENTRADAS IN (1, 9, 20, 21)
            """
        )
        print("=== 2026-07-09 stats ===", cur.fetchone())
    finally:
        ds.close()


if __name__ == "__main__":
    asyncio.run(main())
