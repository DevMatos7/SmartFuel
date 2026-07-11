"""Provisiona datasets XPERT ausentes em fontes já existentes."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.erp_integration import ErpSource
from app.services.xpert_source_service import XpertSourceService


async def main() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ErpSource).options(selectinload(ErpSource.datasets)))
        sources = list(result.scalars().all())
        if not sources:
            print("Nenhuma fonte encontrada.")
            return 1
        service = XpertSourceService(db)
        for source in sources:
            created = await service.ensure_missing_datasets(source)
            if created:
                print(f"Fonte {source.code}: datasets criados {created}")
            else:
                print(f"Fonte {source.code}: nenhum dataset ausente")
        await db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
