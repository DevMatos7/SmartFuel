"""Inspect single sync run errors for Etapa C."""

from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.erp_integration import ErpStagingRecord, ErpSyncError

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "de31376c-ab71-4087-805e-55c141003c2b"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        cols = (
            await db.execute(
                text(
                    "select column_name from information_schema.columns "
                    "where table_name='erp_sync_errors' order by 1"
                )
            )
        ).all()
        print("error_cols", [c[0] for c in cols])
        errs = (await db.execute(select(ErpSyncError).where(ErpSyncError.sync_run_id == RUN_ID))).scalars().all()
        print("orm_errors", len(errs))
        for e in errs:
            print(json.dumps({c.name: getattr(e, c.name) for c in e.__table__.columns}, default=str))
        bad = (
            await db.execute(
                select(ErpStagingRecord).where(
                    ErpStagingRecord.sync_run_id == RUN_ID,
                    ErpStagingRecord.processing_status.in_(["ERROR", "QUARANTINED"]),
                )
            )
        ).scalars().all()
        print("bad_staging", len(bad))
        for s in bad:
            print(
                json.dumps(
                    {
                        "source_key": s.source_key,
                        "status": s.processing_status,
                        "validation_errors": s.validation_errors,
                        "product": (s.normalized_payload or {}).get("source_product_id"),
                        "cfop": (s.normalized_payload or {}).get("source_cfop"),
                        "cancelled": (s.normalized_payload or {}).get("source_cancelled"),
                    },
                    ensure_ascii=False,
                )
            )
        counts = (
            await db.execute(
                text(
                    "select processing_status, count(*) from erp_staging_records "
                    "where sync_run_id=:r group by 1"
                ),
                {"r": RUN_ID},
            )
        ).all()
        print("status_counts", counts)


if __name__ == "__main__":
    asyncio.run(main())
