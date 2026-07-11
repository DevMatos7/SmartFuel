"""Sprint 8.2 — cobertura XPERT×PG + diagnóstico de prontidão (somente leitura).

Uso:
  python scripts/homolog_sprint82_coverage.py [station_erp_id=2443] [station_uuid?]

Gera:
  docs/sprints/sprint-08-2-coverage.json
  docs/sprints/sprint-08-2-coverage.md
  docs/sprints/sprint-08-2-product-diag.json
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource
from app.models.erp_product import ErpProduct
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.product import Product
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.station import Station

BRANCH = int(sys.argv[1]) if len(sys.argv) > 1 else 2443
STATION_UUID = (
    uuid.UUID(sys.argv[2])
    if len(sys.argv) > 2
    else uuid.UUID("1edc5c8b-0ba1-405c-a000-03e61e31521e")
)
WINDOWS = (1, 7, 30)
DIAG_PRODUCTS = ("1505", "1506")


def _out_dir() -> Path:
    env = os.environ.get("SPRINT_DOCS_DIR")
    if env:
        path = Path(env)
        path.mkdir(parents=True, exist_ok=True)
        return path
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        docs = root / "docs"
        if docs.is_dir():
            out = docs / "sprints"
            out.mkdir(parents=True, exist_ok=True)
            return out
    path = Path("/tmp/sprint-docs")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dec(v) -> str | None:
    if v is None:
        return None
    return str(v)


async def _pg_window(db, station_id: uuid.UUID, date_from: date, date_to: date) -> dict:
    inv_q = select(FuelPurchaseInvoice).where(
        FuelPurchaseInvoice.station_id == station_id,
        FuelPurchaseInvoice.entry_date >= date_from,
        FuelPurchaseInvoice.entry_date <= date_to,
    )
    invoices = list((await db.execute(inv_q)).scalars().all())
    inv_ids = [i.id for i in invoices]
    items: list[FuelPurchaseItem] = []
    if inv_ids:
        items = list(
            (
                await db.execute(
                    select(FuelPurchaseItem).where(FuelPurchaseItem.purchase_invoice_id.in_(inv_ids))
                )
            )
            .scalars()
            .all()
        )

    days_with = sorted({i.entry_date.isoformat() for i in invoices})
    mapped = sum(1 for i in items if i.canonical_product_id is not None)
    vol_ok = sum(1 for i in items if i.volume_liters is not None and i.volume_liters > 0)
    cost_ok = sum(
        1 for i in items if i.commercial_delivered_cost is not None and i.commercial_delivered_cost > 0
    )
    cancelled_inv = sum(1 for i in invoices if i.is_cancelled)
    returns = sum(1 for i in invoices if i.operation_type == "PURCHASE_RETURN")
    units: dict[str, int] = {}
    for it in items:
        u = (it.source_unit or "").strip() or "(vazio)"
        units[u] = units.get(u, 0) + 1

    return {
        "invoices_pg": len(invoices),
        "items_pg": len(items),
        "cancelled_invoices_pg": cancelled_inv,
        "purchase_returns_pg": returns,
        "days_with_purchases_pg": len(days_with),
        "days_list_pg": days_with,
        "items_mapped_pg": mapped,
        "items_volume_gt0_pg": vol_ok,
        "items_cost_gt0_pg": cost_ok,
        "source_units_pg": units,
        "first_entry_date_pg": min(days_with) if days_with else None,
        "last_entry_date_pg": max(days_with) if days_with else None,
    }


def _xpert_window(cur, branch: int, date_from: date, date_to_exclusive: date) -> dict:
    cur.execute(
        f"""
        SELECT COUNT(*) FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{date_from.isoformat()}'
          AND C.DTACONTA < '{date_to_exclusive.isoformat()}'
        """
    )
    invoices = int(cur.fetchone()[0])

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM ITENSMOVPRODUTOS I
        INNER JOIN MOVPRODUTOS M
          ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS AND I.ID_FILIAL = M.ID_FILIAL AND I.ID_DB = M.ID_DB
        INNER JOIN COMPROVANTES C
          ON C.ID_COMPROVANTE = M.ID_COMPROVANTE AND C.ID_FILIAL = M.ID_FILIAL AND C.ID_DB = M.ID_DB
        WHERE I.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{date_from.isoformat()}'
          AND C.DTACONTA < '{date_to_exclusive.isoformat()}'
        """
    )
    items = int(cur.fetchone()[0])

    cur.execute(
        f"""
        SELECT COUNT(DISTINCT CONVERT(date, C.DTACONTA))
        FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{date_from.isoformat()}'
          AND C.DTACONTA < '{date_to_exclusive.isoformat()}'
        """
    )
    days = int(cur.fetchone()[0])

    cur.execute(
        f"""
        SELECT MIN(CONVERT(date, C.DTACONTA)), MAX(CONVERT(date, C.DTACONTA))
        FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{date_from.isoformat()}'
          AND C.DTACONTA < '{date_to_exclusive.isoformat()}'
        """
    )
    first_last = cur.fetchone()
    first_x = first_last[0].isoformat() if first_last and first_last[0] else None
    last_x = first_last[1].isoformat() if first_last and first_last[1] else None

    cur.execute(
        f"""
        SELECT TOP 15 P.UNIDADE, COUNT(*) CNT
        FROM ITENSMOVPRODUTOS I
        INNER JOIN MOVPRODUTOS M
          ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS AND I.ID_FILIAL = M.ID_FILIAL AND I.ID_DB = M.ID_DB
        INNER JOIN COMPROVANTES C
          ON C.ID_COMPROVANTE = M.ID_COMPROVANTE AND C.ID_FILIAL = M.ID_FILIAL AND C.ID_DB = M.ID_DB
        INNER JOIN PRODUTOS P ON P.ID_PRODUTOS = I.ID_PRODUTOS AND P.ID_FILIAL = I.ID_FILIAL
        WHERE I.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{date_from.isoformat()}'
          AND C.DTACONTA < '{date_to_exclusive.isoformat()}'
        GROUP BY P.UNIDADE
        ORDER BY CNT DESC
        """
    )
    units = {str(r[0] or "(vazio)"): int(r[1]) for r in cur.fetchall()}

    return {
        "invoices_xpert": invoices,
        "items_xpert": items,
        "days_with_purchases_xpert": days,
        "first_entry_date_xpert": first_x,
        "last_entry_date_xpert": last_x,
        "source_units_xpert": units,
    }


def _diag_products_xpert(cur, branch: int) -> tuple[list[dict], list[dict]]:
    ids = ",".join(DIAG_PRODUCTS)
    cur.execute(
        f"""
        SELECT
          CAST(P.ID_PRODUTOS AS VARCHAR(50)),
          CAST(P.NOMEPRODUTO AS VARCHAR(255)),
          CAST(P.UNIDADE AS VARCHAR(30)),
          CAST(P.NCM AS VARCHAR(20)),
          CAST(P.ID_FILIAL AS VARCHAR(20))
        FROM PRODUTOS P
        WHERE P.ID_FILIAL = {branch}
          AND P.ID_PRODUTOS IN ({ids})
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "erp_product_id": r[0],
                "name": r[1],
                "unit": r[2],
                "ncm": r[3],
                "branch_id": r[4],
            }
        )

    # Movimentos recentes (90d) desses produtos
    end = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=90)
    cur.execute(
        f"""
        SELECT
          CAST(I.ID_PRODUTOS AS VARCHAR(50)),
          CAST(C.ID_COMPROVANTE AS VARCHAR(50)),
          CONVERT(varchar(10), C.DTACONTA, 23),
          CAST(ROUND(I.QTDE, 6) AS DECIMAL(20,6)),
          CAST(P.UNIDADE AS VARCHAR(30)),
          CAST(P.NOMEPRODUTO AS VARCHAR(255)),
          CAST(ROUND(I.VLRUNITARIO, 8) AS DECIMAL(20,8)),
          CAST(ROUND(I.TOTAL, 4) AS DECIMAL(22,4))
        FROM ITENSMOVPRODUTOS I
        INNER JOIN MOVPRODUTOS M
          ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS AND I.ID_FILIAL = M.ID_FILIAL AND I.ID_DB = M.ID_DB
        INNER JOIN COMPROVANTES C
          ON C.ID_COMPROVANTE = M.ID_COMPROVANTE AND C.ID_FILIAL = M.ID_FILIAL AND C.ID_DB = M.ID_DB
        INNER JOIN PRODUTOS P ON P.ID_PRODUTOS = I.ID_PRODUTOS AND P.ID_FILIAL = I.ID_FILIAL
        WHERE I.ID_FILIAL = {branch}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND I.ID_PRODUTOS IN ({ids})
          AND C.DTACONTA >= '{start.isoformat()}'
          AND C.DTACONTA < '{end.isoformat()}'
        ORDER BY C.DTACONTA DESC
        """
    )
    movements = []
    for r in cur.fetchall():
        movements.append(
            {
                "erp_product_id": r[0],
                "source_invoice_id": r[1],
                "entry_date": r[2],
                "source_quantity": _dec(r[3]),
                "source_unit": r[4],
                "product_name": r[5],
                "unit_price": _dec(r[6]),
                "item_total": _dec(r[7]),
            }
        )
    return rows, movements


async def _diag_products_pg(db, station_id: uuid.UUID) -> dict:
    erp_rows = list(
        (
            await db.execute(
                select(ErpProduct).where(
                    ErpProduct.station_id == station_id,
                    ErpProduct.erp_product_id.in_(list(DIAG_PRODUCTS)),
                )
            )
        )
        .scalars()
        .all()
    )
    items = list(
        (
            await db.execute(
                select(FuelPurchaseItem).where(
                    FuelPurchaseItem.station_id == station_id,
                    FuelPurchaseItem.source_product_id.in_(list(DIAG_PRODUCTS)),
                )
            )
        )
        .scalars()
        .all()
    )
    canons = {}
    for e in erp_rows:
        if e.canonical_product_id:
            p = (
                await db.execute(select(Product).where(Product.id == e.canonical_product_id))
            ).scalar_one_or_none()
            if p:
                canons[str(e.erp_product_id)] = {
                    "canonical_id": str(p.id),
                    "code": p.code,
                    "name": p.name,
                    "fuel_family": p.fuel_family,
                    "unit": p.unit,
                }

    return {
        "erp_products": [
            {
                "erp_product_id": e.erp_product_id,
                "description": e.erp_description,
                "unit": e.erp_unit,
                "mapping_status": e.mapping_status,
                "canonical_product_id": str(e.canonical_product_id) if e.canonical_product_id else None,
                "canonical": canons.get(str(e.erp_product_id)),
            }
            for e in erp_rows
        ],
        "purchase_items": [
            {
                "id": str(i.id),
                "source_invoice_id": i.source_invoice_id,
                "source_product_id": i.source_product_id,
                "source_description": i.source_description,
                "source_unit": i.source_unit,
                "source_quantity": _dec(i.source_quantity),
                "volume_liters": _dec(i.volume_liters),
                "commercial_delivered_cost": _dec(i.commercial_delivered_cost),
                "canonical_product_id": str(i.canonical_product_id) if i.canonical_product_id else None,
                "metric_eligibility_status": i.metric_eligibility_status,
                "metric_exclusion_reasons": i.metric_exclusion_reasons,
            }
            for i in items
        ],
    }


async def _quote_readiness(db, station_id: uuid.UUID) -> dict:
    active = (
        await db.execute(
            select(func.count())
            .select_from(Quote)
            .where(Quote.station_id == station_id, Quote.activated_at.isnot(None))
        )
    ).scalar_one()
    first = (
        await db.execute(
            select(func.min(Quote.activated_at)).where(
                Quote.station_id == station_id, Quote.activated_at.isnot(None)
            )
        )
    ).scalar_one()
    last = (
        await db.execute(
            select(func.max(Quote.activated_at)).where(
                Quote.station_id == station_id, Quote.activated_at.isnot(None)
            )
        )
    ).scalar_one()
    items = (
        await db.execute(
            select(func.count())
            .select_from(QuoteItem)
            .join(Quote, Quote.id == QuoteItem.quote_id)
            .where(Quote.station_id == station_id, Quote.activated_at.isnot(None))
        )
    ).scalar_one()
    return {
        "activated_quotes": int(active),
        "activated_quote_items": int(items),
        "first_activated_at": first.isoformat() if first else None,
        "last_activated_at": last.isoformat() if last else None,
    }


async def _pg_global_coverage(db, station_id: uuid.UUID) -> dict:
    first = (
        await db.execute(
            select(func.min(FuelPurchaseInvoice.entry_date)).where(
                FuelPurchaseInvoice.station_id == station_id
            )
        )
    ).scalar_one()
    last = (
        await db.execute(
            select(func.max(FuelPurchaseInvoice.entry_date)).where(
                FuelPurchaseInvoice.station_id == station_id
            )
        )
    ).scalar_one()
    days = (
        await db.execute(
            select(func.count(func.distinct(FuelPurchaseInvoice.entry_date))).where(
                FuelPurchaseInvoice.station_id == station_id
            )
        )
    ).scalar_one()
    inv = (
        await db.execute(
            select(func.count())
            .select_from(FuelPurchaseInvoice)
            .where(FuelPurchaseInvoice.station_id == station_id)
        )
    ).scalar_one()
    items = (
        await db.execute(
            select(func.count())
            .select_from(FuelPurchaseItem)
            .where(FuelPurchaseItem.station_id == station_id)
        )
    ).scalar_one()
    return {
        "first_purchase_day_pg": first.isoformat() if first else None,
        "last_purchase_day_pg": last.isoformat() if last else None,
        "days_with_purchases_pg_all": int(days),
        "invoices_pg_all": int(inv),
        "items_pg_all": int(items),
    }


async def main() -> None:
    today = date.today()
    out_dir = _out_dir()

    async with AsyncSessionLocal() as db:
        station = (
            await db.execute(select(Station).where(Station.id == STATION_UUID))
        ).scalar_one_or_none()
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
        pg_global = await _pg_global_coverage(db, STATION_UUID)
        quote_ready = await _quote_readiness(db, STATION_UUID)
        pg_diag = await _diag_products_pg(db, STATION_UUID)

        windows_out = []
        ds = DirectSqlServerDataSource(source)
        conn = ds._connect()  # noqa: SLF001
        cur = conn.cursor()
        try:
            xpert_diag, movements = _diag_products_xpert(cur, BRANCH)
            for days in WINDOWS:
                date_from = today - timedelta(days=days - 1)
                date_to = today
                date_to_excl = today + timedelta(days=1)
                xpert = _xpert_window(cur, BRANCH, date_from, date_to_excl)
                pg = await _pg_window(db, STATION_UUID, date_from, date_to)
                windows_out.append(
                    {
                        "window_days": days,
                        "searched_period": {
                            "from": date_from.isoformat(),
                            "to": date_to.isoformat(),
                        },
                        "xpert": xpert,
                        "postgres": pg,
                        "gap": {
                            "invoices_missing_in_pg": max(
                                0, xpert["invoices_xpert"] - pg["invoices_pg"]
                            ),
                            "items_missing_in_pg": max(0, xpert["items_xpert"] - pg["items_pg"]),
                            "interpretation": (
                                "PG cobre apenas o subconjunto sincronizado; "
                                "janela pesquisada ≠ cobertura carregada."
                                if xpert["invoices_xpert"] > pg["invoices_pg"]
                                else "Contagens alinhadas ou PG >= XPERT na janela."
                            ),
                        },
                    }
                )
        finally:
            ds.close()

    coverage = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "station": {
            "id": str(STATION_UUID),
            "erp_branch_id": BRANCH,
            "trade_name": station.trade_name if station else None,
        },
        "pg_loaded_coverage": pg_global,
        "quote_readiness": quote_ready,
        "windows": windows_out,
        "formal_statement": {
            "comparable_in_available_pg_data": 0,
            "comparable_in_xpert_90d": "UNKNOWN_UNTIL_SYNC_AND_MAPPING",
            "note": (
                "REAL_COMPARABLE_PURCHASES=0 refere-se aos dados disponíveis no PostgreSQL, "
                "não ao universo completo de compras do XPERT no período pesquisado."
            ),
        },
    }

    product_diag = {
        "products_of_interest": list(DIAG_PRODUCTS),
        "xpert_cadastro": xpert_diag,
        "xpert_movements_90d": movements,
        "postgres": pg_diag,
        "volume_diagnosis_rules": {
            "volume_liters_set_only_when_unit_in": ["L", "LT", "LITRO", "LITROS", "LITER", "LITERS"],
            "empty_or_other_unit": "UNIT_CONVERSION_REQUIRED — volume_liters permanece NULL/0",
            "do_not": "Estimar litros a partir do valor monetário",
            "required_for_benchmark": [
                "volume_liters > 0",
                "conversion explícita válida (ainda sem fator cadastrado para UN)",
            ],
        },
        "three_independent_blocks": [
            {
                "id": 1,
                "name": "UNMAPPED_PRODUCT",
                "status": "OPEN",
                "detail": "1505/1506 sem canonical_product_id no PG",
            },
            {
                "id": 2,
                "name": "VOLUME_ZERO_OR_NULL",
                "status": "OPEN",
                "detail": "Unidade XPERT provavelmente não-litro (ex.: UN); conversão não inventada",
            },
            {
                "id": 3,
                "name": "NO_HISTORICAL_QUOTES",
                "status": "OPEN",
                "detail": f"activated_quotes={quote_ready['activated_quotes']} no posto",
            },
        ],
    }

    cov_json = out_dir / "sprint-08-2-coverage.json"
    diag_json = out_dir / "sprint-08-2-product-diag.json"
    cov_md = out_dir / "sprint-08-2-coverage.md"
    cov_json.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")
    diag_json.write_text(json.dumps(product_diag, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Sprint 8.2 — Cobertura XPERT × PostgreSQL",
        "",
        f"Posto: `{STATION_UUID}` · Filial ERP `{BRANCH}`",
        "",
        "## Cobertura efetivamente carregada no PG (todas as datas)",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Primeiro dia de compra no PG | {pg_global['first_purchase_day_pg']} |",
        f"| Último dia de compra no PG | {pg_global['last_purchase_day_pg']} |",
        f"| Dias com compras no PG | {pg_global['days_with_purchases_pg_all']} |",
        f"| Notas no PG | {pg_global['invoices_pg_all']} |",
        f"| Itens no PG | {pg_global['items_pg_all']} |",
        f"| Cotações ativadas no posto | {quote_ready['activated_quotes']} |",
        "",
        "## Janelas pesquisadas vs origem",
        "",
    ]
    for w in windows_out:
        sp = w["searched_period"]
        x = w["xpert"]
        p = w["postgres"]
        g = w["gap"]
        lines.extend(
            [
                f"### {w['window_days']} dia(s) — pesquisado `{sp['from']}` → `{sp['to']}`",
                "",
                "| Métrica | XPERT | PostgreSQL |",
                "|---------|-------|------------|",
                f"| Notas | {x['invoices_xpert']} | {p['invoices_pg']} |",
                f"| Itens | {x['items_xpert']} | {p['items_pg']} |",
                f"| Dias com compra | {x['days_with_purchases_xpert']} | {p['days_with_purchases_pg']} |",
                f"| Primeiro dia na janela | {x['first_entry_date_xpert']} | {p['first_entry_date_pg']} |",
                f"| Último dia na janela | {x['last_entry_date_xpert']} | {p['last_entry_date_pg']} |",
                f"| Itens mapeados | — | {p['items_mapped_pg']} |",
                f"| Itens volume>0 | — | {p['items_volume_gt0_pg']} |",
                "",
                f"Gap notas: **{g['invoices_missing_in_pg']}** · Gap itens: **{g['items_missing_in_pg']}**",
                "",
                f"_{g['interpretation']}_",
                "",
                f"Unidades XPERT: `{x['source_units_xpert']}`",
                f"Unidades PG: `{p['source_units_pg']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretação formal",
            "",
            "- `compras comparáveis nos dados disponíveis no PG = 0`",
            "- **não** afirmar ainda: `compras comparáveis no XPERT em 90 dias = 0`",
            "- Agenda XPERT permanece bloqueada; expansões de carga são manuais.",
            "",
            "## Produtos 1505 / 1506",
            "",
        ]
    )
    if xpert_diag:
        lines.append("| ERP ID | Nome | Unidade | NCM |")
        lines.append("|--------|------|---------|-----|")
        for r in xpert_diag:
            lines.append(f"| {r['erp_product_id']} | {r['name']} | {r['unit']} | {r['ncm']} |")
    else:
        lines.append("Cadastro não encontrado no XPERT para a filial (verificar sync PRODUCTS).")
    lines.append("")
    lines.append(f"Movimentos 90d no XPERT: **{len(movements)}**")
    lines.append("")
    lines.append("Ver `sprint-08-2-product-diag.json` para itens PG e exclusões.")

    cov_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": cov_json.name, "diag": diag_json.name, "md": cov_md.name}, indent=2))
    print(
        json.dumps(
            {
                "pg_loaded": pg_global,
                "windows_summary": [
                    {
                        "days": w["window_days"],
                        "xpert_invoices": w["xpert"]["invoices_xpert"],
                        "pg_invoices": w["postgres"]["invoices_pg"],
                        "gap_invoices": w["gap"]["invoices_missing_in_pg"],
                    }
                    for w in windows_out
                ],
                "quote_readiness": quote_ready,
                "xpert_products": xpert_diag,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
