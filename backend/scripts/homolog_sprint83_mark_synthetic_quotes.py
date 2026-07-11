"""Marca cotações de exemplo da Sprint 8.2 como SYNTHETIC_TEST."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.core.quote_enums import QuoteOrigin
from app.models.quote import Quote

STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
NOTE_MARKER = "Cotação de exemplo operacional"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        q = await db.execute(
            select(Quote).where(
                Quote.station_id == STATION,
                Quote.notes.ilike(f"%{NOTE_MARKER}%"),
            )
        )
        rows = list(q.scalars().all())
        if not rows:
            # fallback: DIST-EX quotes notes / recent homolog
            q2 = await db.execute(
                select(Quote).where(
                    Quote.station_id == STATION,
                    Quote.seller_name == "Homolog Sprint 8.2",
                )
            )
            rows = list(q2.scalars().all())
        for quote in rows:
            quote.origin = QuoteOrigin.SYNTHETIC_TEST.value
            quote.analytics_eligible = False
        await db.commit()
        payload = {
            "marked": len(rows),
            "quote_ids": [str(r.id) for r in rows],
            "quote_numbers": [r.quote_number for r in rows],
            "origin": QuoteOrigin.SYNTHETIC_TEST.value,
            "analytics_eligible": False,
        }
        print(json.dumps(payload, indent=2))
        out = Path("/tmp/sprint-docs")
        out.mkdir(parents=True, exist_ok=True)
        (out / "sprint-08-3-synthetic-quotes.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
