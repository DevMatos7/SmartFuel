"""Diagnóstico pós-sync 7d + mapeamento combustível com unidade XPERT."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.core.master_data_enums import MappingStatus
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource
from app.models.erp_product import ErpProduct
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.product import Product
from app.services.fuel_purchase_aggregation_service import (
    FuelPurchaseAggregationService,
    PurchaseAggregationKey,
)
from app.services.fuel_purchases_apply_service import LITER_UNITS
from app.core.fuel_purchases_enums import PurchaseMetricEligibilityStatus, PurchaseMetricExclusionReason
from app.core.fuel_purchases_normalization import delivered_cost_per_liter
from decimal import Decimal

STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
BASE = "http://localhost:8000/api/v1"
FUEL_MAP = {
    "1": "ETANOL_HIDRATADO",
    "2": "GASOLINA_C_COMUM",
    "4": "DIESEL_B_S10_COMUM",
    "1272": "ETANOL_HIDRATADO",
    "1271": "GASOLINA_C_ADITIVADA",
}


async def diagnose() -> dict:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
        ds = DirectSqlServerDataSource(source)
        conn = ds._connect()  # noqa: SLF001
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT COUNT(*), MIN(CONVERT(date,C.DTACONTA)), MAX(CONVERT(date,C.DTACONTA))
                FROM COMPROVANTES C
                WHERE C.ID_FILIAL=2443 AND C.SAIDAS_ENTRADAS IN (1,9,21)
                  AND C.DTACONTA >= '2026-07-03' AND C.DTACONTA < '2026-07-10'
                """
            )
            inv = cur.fetchone()
            cur.execute(
                """
                SELECT COUNT(*),
                  SUM(CASE WHEN UPPER(P.UNIDADE) IN ('L','LT','LITRO','LITROS') THEN 1 ELSE 0 END),
                  SUM(CASE WHEN UPPER(ISNULL(P.UNIDADE,'')) = 'UN' THEN 1 ELSE 0 END)
                FROM ITENSMOVPRODUTOS I
                INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
                INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
                INNER JOIN PRODUTOS P ON P.ID_PRODUTOS=I.ID_PRODUTOS AND P.ID_FILIAL=I.ID_FILIAL
                WHERE I.ID_FILIAL=2443 AND C.SAIDAS_ENTRADAS IN (1,9,21)
                  AND C.DTACONTA >= '2026-07-03' AND C.DTACONTA < '2026-07-10'
                """
            )
            items = cur.fetchone()
            cur.execute(
                """
                SELECT CONVERT(varchar(10),C.DTACONTA,23), COUNT(*)
                FROM COMPROVANTES C
                WHERE C.ID_FILIAL=2443 AND C.SAIDAS_ENTRADAS IN (1,9,21)
                  AND C.DTACONTA >= '2026-07-03' AND C.DTACONTA < '2026-07-10'
                GROUP BY CONVERT(varchar(10),C.DTACONTA,23) ORDER BY 1
                """
            )
            by_day = cur.fetchall()
            cur.execute(
                """
                SELECT CAST(C.ID_COMPROVANTE AS varchar(20)), CONVERT(varchar(10),C.DTACONTA,23),
                  (SELECT COUNT(*) FROM MOVPRODUTOS M
                    INNER JOIN ITENSMOVPRODUTOS I ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS
                      AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
                    WHERE M.ID_COMPROVANTE=C.ID_COMPROVANTE AND M.ID_FILIAL=C.ID_FILIAL AND M.ID_DB=C.ID_DB)
                FROM COMPROVANTES C
                WHERE C.ID_FILIAL=2443 AND C.SAIDAS_ENTRADAS IN (1,9,21)
                  AND C.DTACONTA >= '2026-07-03' AND C.DTACONTA < '2026-07-10'
                ORDER BY C.DTACONTA
                """
            )
            inv_items = [
                {"source_invoice_id": r[0], "day": r[1], "item_count": int(r[2])} for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT CAST(P.ID_PRODUTOS AS varchar(20)), CAST(P.NOMEPRODUTO AS varchar(80)),
                       CAST(P.UNIDADE AS varchar(20))
                FROM PRODUTOS P
                WHERE P.ID_FILIAL=2443 AND P.ID_PRODUTOS IN (1,2,4,1271,1272)
                """
            )
            fuel_units = [{"id": r[0], "name": r[1], "unit": r[2]} for r in cur.fetchall()]
        finally:
            ds.close()

        pg_days = (
            await db.execute(
                select(FuelPurchaseInvoice.entry_date, func.count())
                .where(
                    FuelPurchaseInvoice.station_id == STATION,
                    FuelPurchaseInvoice.entry_date >= date(2026, 7, 3),
                    FuelPurchaseInvoice.entry_date <= date(2026, 7, 9),
                )
                .group_by(FuelPurchaseInvoice.entry_date)
                .order_by(FuelPurchaseInvoice.entry_date)
            )
        ).all()
        return {
            "xpert_invoices": {"count": inv[0], "min": str(inv[1]), "max": str(inv[2])},
            "xpert_items": {"count": items[0], "lt": int(items[1] or 0), "un": int(items[2] or 0)},
            "xpert_by_day": [{"day": r[0], "count": r[1]} for r in by_day],
            "xpert_invoice_item_counts": inv_items,
            "xpert_fuel_units": fuel_units,
            "pg_by_day": [{"day": str(r[0]), "count": r[1]} for r in pg_days],
            "invoices_without_items_xpert": sum(1 for r in inv_items if r["item_count"] == 0),
        }


async def map_fuel_from_xpert_unit() -> dict:
    client = httpx.Client(base_url=BASE, timeout=60)
    token = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "SenhaSegura123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        # Confirm LT from XPERT
        diag = await diagnose()
        xpert_units = {p["id"]: p for p in diag["xpert_fuel_units"]}
        products = {p.code: p for p in (await db.execute(select(Product))).scalars().all()}
        results = []
        for erp_id, code in FUEL_MAP.items():
            xu = xpert_units.get(erp_id)
            if not xu or (xu["unit"] or "").upper() not in {"L", "LT", "LITRO", "LITROS", "LITER", "LITERS"}:
                results.append({"erp_id": erp_id, "skipped": "xpert_unit_not_lt", "xpert": xu})
                continue
            erp = (
                await db.execute(
                    select(ErpProduct).where(
                        ErpProduct.station_id == STATION, ErpProduct.erp_product_id == erp_id
                    )
                )
            ).scalar_one_or_none()
            canon = products.get(code)
            if erp is None or canon is None:
                results.append({"erp_id": erp_id, "skipped": "missing_row"})
                continue
            # Atualiza unidade no mestre a partir do XPERT (cadastro incompleto no sync PRODUCTS)
            if not erp.erp_unit:
                erp.erp_unit = xu["unit"]
                await db.commit()
            resp = client.post(
                f"/erp-products/{erp.id}/map",
                headers=headers,
                json={
                    "canonical_product_id": str(canon.id),
                    "reason": (
                        f"Sprint 8.2 — XPERT {xu['name']} unidade {xu['unit']} "
                        f"filial 2443 → {code}"
                    ),
                },
            )
            results.append(
                {
                    "erp_id": erp_id,
                    "canonical": code,
                    "xpert_unit": xu["unit"],
                    "http": resp.status_code,
                    "body": resp.text[:200],
                }
            )
        return {"diag": diag, "mapped": results}


async def main() -> None:
    out = await map_fuel_from_xpert_unit()
    path = Path("/tmp/sprint-docs/sprint-08-2-fuel-map-fix.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
