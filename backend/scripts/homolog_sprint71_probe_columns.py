"""Diagnóstico de colunas XPERT para Sprint 7.1."""

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
    conn = ds._connect()  # noqa: SLF001
    cur = conn.cursor()
    try:
        for table in ("CONTASPAGAR", "COMPROVANTES", "ITENSMOVPRODUTOS", "PRODUTOS"):
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
                table,
            )
            rows = cur.fetchall()
            print(f"=== {table} ({len(rows)}) ===")
            for r in rows:
                print(f"  {r[0]}: {r[1]}")

        cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'CONTASPAGAR' AND ("
            "COLUMN_NAME LIKE '%COMPROV%' OR COLUMN_NAME LIKE '%REF%' OR "
            "COLUMN_NAME LIKE '%DOC%' OR COLUMN_NAME LIKE '%NF%' OR "
            "COLUMN_NAME LIKE '%CHAVE%' OR COLUMN_NAME LIKE '%MOV%' OR "
            "COLUMN_NAME LIKE '%ID_%')"
        )
        print("=== CONTASPAGAR link-like ===")
        for r in cur.fetchall():
            print(f"  {r[0]}")

        cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'COMPROVANTES' AND ("
            "COLUMN_NAME LIKE '%CHAVE%' OR COLUMN_NAME LIKE '%FRETE%' OR "
            "COLUMN_NAME LIKE '%DESCON%' OR COLUMN_NAME LIKE '%SEGURO%' OR "
            "COLUMN_NAME LIKE '%XML%' OR COLUMN_NAME LIKE '%ACESSO%' OR "
            "COLUMN_NAME LIKE '%SERIE%' OR COLUMN_NAME LIKE '%VLR%')"
        )
        print("=== COMPROVANTES fiscal/freight-like ===")
        for r in cur.fetchall():
            print(f"  {r[0]}")

        cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'ITENSMOVPRODUTOS' AND ("
            "COLUMN_NAME LIKE '%ICMS%' OR COLUMN_NAME LIKE '%PIS%' OR "
            "COLUMN_NAME LIKE '%COFINS%' OR COLUMN_NAME LIKE '%FRETE%' OR "
            "COLUMN_NAME LIKE '%DESCON%' OR COLUMN_NAME LIKE '%UNID%' OR "
            "COLUMN_NAME LIKE '%VLR%' OR COLUMN_NAME LIKE '%CUSTO%')"
        )
        print("=== ITENS tax/freight/cost-like ===")
        for r in cur.fetchall():
            print(f"  {r[0]}")

        cur.execute(
            """
            SELECT TOP 5
                C.ID_COMPROVANTE, C.NROCOMPROVANTE, C.ID_ENTIDADE,
                C.DTACONTA, C.DTAEMISSAO, C.DATA, C.VLRTOTAL, C.CANCELADO,
                C.SAIDAS_ENTRADAS, C.CFOP, C.REFERENCIA
            FROM COMPROVANTES C
            WHERE C.ID_FILIAL = 2443
              AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
              AND C.DTACONTA >= '2026-07-01'
              AND C.DTACONTA < '2026-07-10'
            ORDER BY C.DTACONTA DESC
            """
        )
        print("=== SAMPLE ENTRIES ===")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            print(dict(zip(cols, row, strict=False)))

        cur.execute(
            """
            SELECT TOP 5
                CP.ID_CONTASPAGAR, CP.ID_FILIAL, CP.ID_ENTIDADE, CP.NRODOC,
                CP.DTACONTA, CP.DTAVCTO, CP.VALOR, CP.DTAPGTO, CP.REFERENCIAPGTO,
                CP.HISTORICO
            FROM CONTASPAGAR CP
            WHERE CP.ID_FILIAL = 2443
              AND CP.DTACONTA >= '2026-07-01'
              AND CP.DTACONTA < '2026-07-10'
            ORDER BY CP.DTACONTA DESC
            """
        )
        print("=== SAMPLE AP ===")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            print(dict(zip(cols, row, strict=False)))
    finally:
        ds.close()


if __name__ == "__main__":
    asyncio.run(main())
