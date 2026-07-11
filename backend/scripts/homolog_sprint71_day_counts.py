"""Contagens e duplicidades — um dia filial 2443."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-07-09"
BRANCH = 2443


async def main() -> None:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    conn = ds._connect()  # noqa: SLF001
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT COUNT(*) FROM COMPROVANTES C
            WHERE C.ID_FILIAL = {BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
              AND C.DTACONTA >= '{DAY}'
              AND C.DTACONTA < DATEADD(day, 1, '{DAY}')
            """
        )
        print("invoices", cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT COUNT(*) FROM (
              SELECT C.ID_COMPROVANTE
              FROM COMPROVANTES C
              WHERE C.ID_FILIAL = {BRANCH}
                AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
                AND C.DTACONTA >= '{DAY}'
                AND C.DTACONTA < DATEADD(day, 1, '{DAY}')
              GROUP BY C.ID_COMPROVANTE
              HAVING COUNT(*) > 1
            ) D
            """
        )
        print("invoice_dup_keys", cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM ITENSMOVPRODUTOS I
            INNER JOIN MOVPRODUTOS M
              ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS AND I.ID_FILIAL = M.ID_FILIAL AND I.ID_DB = M.ID_DB
            INNER JOIN COMPROVANTES C
              ON C.ID_COMPROVANTE = M.ID_COMPROVANTE AND C.ID_FILIAL = M.ID_FILIAL AND C.ID_DB = M.ID_DB
            WHERE I.ID_FILIAL = {BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
              AND C.DTACONTA >= '{DAY}'
              AND C.DTACONTA < DATEADD(day, 1, '{DAY}')
            """
        )
        print("items", cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT COUNT(*) FROM (
              SELECT I.ID_ITENSMOVPRODUTOS
              FROM ITENSMOVPRODUTOS I
              INNER JOIN MOVPRODUTOS M
                ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS AND I.ID_FILIAL = M.ID_FILIAL AND I.ID_DB = M.ID_DB
              INNER JOIN COMPROVANTES C
                ON C.ID_COMPROVANTE = M.ID_COMPROVANTE AND C.ID_FILIAL = M.ID_FILIAL AND C.ID_DB = M.ID_DB
              WHERE I.ID_FILIAL = {BRANCH}
                AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
                AND C.DTACONTA >= '{DAY}'
                AND C.DTACONTA < DATEADD(day, 1, '{DAY}')
              GROUP BY I.ID_ITENSMOVPRODUTOS
              HAVING COUNT(*) > 1
            ) D
            """
        )
        print("item_dup_keys", cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT COUNT(*) FROM CONTASPAGAR CP
            WHERE CP.ID_FILIAL = {BRANCH}
              AND CP.DTACONTA >= '{DAY}'
              AND CP.DTACONTA < DATEADD(day, 1, '{DAY}')
            """
        )
        print("titles_all", cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT TOP 3 P.UNIDADE, COUNT(*) CNT
            FROM ITENSMOVPRODUTOS I
            INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
            INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
            INNER JOIN PRODUTOS P ON P.ID_PRODUTOS=I.ID_PRODUTOS AND P.ID_FILIAL=I.ID_FILIAL
            WHERE I.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{DAY}' AND C.DTACONTA < DATEADD(day,1,'{DAY}')
            GROUP BY P.UNIDADE ORDER BY CNT DESC
            """
        )
        print("units", cur.fetchall())
    finally:
        ds.close()


if __name__ == "__main__":
    asyncio.run(main())
