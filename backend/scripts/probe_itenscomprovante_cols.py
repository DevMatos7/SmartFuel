"""Probe ITENSCOMPROVANTE columns."""
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
        cur.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'ITENSCOMPROVANTE'
            ORDER BY ORDINAL_POSITION
            """
        )
        for name, dtype in cur.fetchall():
            print(f"{name}\t{dtype}")
    finally:
        ds.close()


if __name__ == "__main__":
    asyncio.run(main())
