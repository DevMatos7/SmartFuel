"""Sprint 8.3 — perfil read-only ITENSMOVPRODUTOS × ITENSCOMPROVANTE.

Uso:
  python scripts/homolog_sprint83_source_profile.py [days=30]
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.models.erp_integration import ErpSource

BRANCH = 2443
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
FUEL_IDS = (1, 2, 4, 1271, 1272)
IGNORE_IDS = (1505, 1506)
LITER_UNITS = ("L", "LT", "LITRO", "LITROS", "LITER", "LITERS")


def _out_dir() -> Path:
    env = os.environ.get("SPRINT_DOCS_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        if (root / "docs").is_dir():
            out = root / "docs" / "sprints"
            out.mkdir(parents=True, exist_ok=True)
            return out
    p = Path("/tmp/sprint-docs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _probe_columns(cur, table: str) -> list[dict]:
    cur.execute(
        f"""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """
    )
    return [
        {
            "name": r[0],
            "type": r[1],
            "length": r[2],
            "nullable": r[3],
        }
        for r in cur.fetchall()
    ]


def _pick(cols: set[str], *candidates: str) -> str | None:
    upper = {c.upper(): c for c in cols}
    for cand in candidates:
        if cand.upper() in upper:
            return upper[cand.upper()]
    return None


def _build_fiscal_select(cols: set[str]) -> tuple[str, dict[str, str | None]]:
    """Monta SELECT fiscal a partir de colunas reais encontradas."""
    mapping = {
        "id": _pick(cols, "ID_ITENSCOMPROVANTE", "ID_ITEMCOMPROVANTE", "ID"),
        "invoice": _pick(cols, "ID_COMPROVANTE"),
        "product": _pick(cols, "ID_PRODUTOS", "ID_PRODUTO"),
        "qty": _pick(cols, "QTDE", "QUANTIDADE", "QTD"),
        "unit_price": _pick(cols, "VLRUNITARIO", "VALORUNITARIO", "PRECO"),
        "total": _pick(cols, "VLRTOTALITEM", "VITEM", "VLRTOTAL", "TOTAL", "VALORTOTAL"),
        "filial": _pick(cols, "ID_FILIAL"),
        "db": _pick(cols, "ID_DB"),
        "desc": _pick(cols, "DESCRICAO", "NOMEPRODUTO", "PRODUTO"),
        "cfop": _pick(cols, "CFOP"),
        "ncm": _pick(cols, "NCM"),
        "discount": _pick(cols, "VLRDESCONTO", "DESCONTO"),
        "seq": _pick(cols, "DFE_NITEM", "NITEM", "SEQUENCIA"),
        "cost": _pick(cols, "VLRCUSTO"),
        "freight": _pick(cols, "VLRFRETE"),
        "insurance": _pick(cols, "VLRSEGURO"),
        "other": _pick(cols, "VLROUTROS"),
        "icms": _pick(cols, "VLRICMSITEM"),
        "icms_st": _pick(cols, "VLRSUBSTITEM"),
        "fcp": _pick(cols, "VALOR_FECOP"),
    }
    if not mapping["invoice"] or not mapping["id"]:
        raise RuntimeError(f"ITENSCOMPROVANTE sem chave mínima: {mapping}")
    # unit pode vir do produto via join
    return mapping


async def main() -> None:
    date_to = date.today()
    date_from = date_to - timedelta(days=DAYS - 1)
    start = date_from.isoformat()
    end_excl = (date_to + timedelta(days=1)).isoformat()
    fuel_in = ",".join(str(i) for i in FUEL_IDS)

    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    conn = ds._connect()  # noqa: SLF001
    cur = conn.cursor()
    out_dir = _out_dir()

    try:
        mov_cols = _probe_columns(cur, "ITENSMOVPRODUTOS")
        fis_cols = _probe_columns(cur, "ITENSCOMPROVANTE")
        fis_names = {c["name"] for c in fis_cols}
        fmap = _build_fiscal_select(fis_names)

        # --- Movimento por nota ---
        cur.execute(
            f"""
            SELECT
              CAST(C.ID_COMPROVANTE AS VARCHAR(50)),
              CAST(C.NROCOMPROVANTE AS VARCHAR(50)),
              CONVERT(varchar(10), C.DTACONTA, 23),
              CAST(C.ID_ENTIDADE AS VARCHAR(50)),
              COUNT(*),
              SUM(CASE WHEN I.ID_PRODUTOS IN ({fuel_in}) THEN 1 ELSE 0 END),
              SUM(CASE WHEN I.ID_PRODUTOS IN ({fuel_in})
                        AND UPPER(ISNULL(P.UNIDADE,'')) IN ('L','LT','LITRO','LITROS','LITER','LITERS')
                       THEN I.QTDE ELSE 0 END),
              SUM(CASE WHEN UPPER(ISNULL(P.UNIDADE,'')) IN ('L','LT','LITRO','LITROS','LITER','LITERS')
                       THEN I.QTDE ELSE 0 END),
              CAST(SUM(CASE WHEN I.VLRCUSTOSEMICMS = 0 THEN I.TOTAL ELSE I.QTDE * I.VLRCUSTOSEMICMS END)
                   AS DECIMAL(22,4)),
              CAST(ISNULL(C.VLRTOTAL,0) AS DECIMAL(22,4))
            FROM COMPROVANTES C
            INNER JOIN MOVPRODUTOS M
              ON M.ID_COMPROVANTE=C.ID_COMPROVANTE AND M.ID_FILIAL=C.ID_FILIAL AND M.ID_DB=C.ID_DB
            INNER JOIN ITENSMOVPRODUTOS I
              ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
            INNER JOIN PRODUTOS P ON P.ID_PRODUTOS=I.ID_PRODUTOS AND P.ID_FILIAL=I.ID_FILIAL
            WHERE C.ID_FILIAL={BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            GROUP BY C.ID_COMPROVANTE, C.NROCOMPROVANTE, CONVERT(varchar(10), C.DTACONTA, 23),
                     C.ID_ENTIDADE, C.VLRTOTAL
            """
        )
        mov_by_inv: dict[str, dict] = {}
        for r in cur.fetchall():
            mov_by_inv[r[0]] = {
                "source_invoice_id": r[0],
                "document_number": r[1],
                "entry_date": r[2],
                "supplier": r[3],
                "items_mov_count": int(r[4]),
                "fuel_mov_rows": int(r[5] or 0),
                "volume_lt_fuel_mov": str(r[6] or 0),
                "volume_lt_mov": str(r[7] or 0),
                "total_mov": str(r[8] or 0),
                "invoice_total": str(r[9] or 0),
            }

        # Todas as notas da janela (mesmo sem itens)
        cur.execute(
            f"""
            SELECT CAST(C.ID_COMPROVANTE AS VARCHAR(50)),
                   CAST(C.NROCOMPROVANTE AS VARCHAR(50)),
                   CONVERT(varchar(10), C.DTACONTA, 23),
                   CAST(C.ID_ENTIDADE AS VARCHAR(50)),
                   CAST(ISNULL(C.VLRTOTAL,0) AS DECIMAL(22,4))
            FROM COMPROVANTES C
            WHERE C.ID_FILIAL={BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            """
        )
        all_invs = {
            r[0]: {
                "source_invoice_id": r[0],
                "document_number": r[1],
                "entry_date": r[2],
                "supplier": r[3],
                "invoice_total": str(r[4] or 0),
            }
            for r in cur.fetchall()
        }

        # --- Fiscal por nota ---
        join_filial = (
            f" AND IC.{fmap['filial']}=C.ID_FILIAL" if fmap["filial"] else ""
        )
        join_db = f" AND IC.{fmap['db']}=C.ID_DB" if fmap["db"] else ""
        qty_expr = f"IC.{fmap['qty']}" if fmap["qty"] else "NULL"
        total_expr = f"IC.{fmap['total']}" if fmap["total"] else "0"
        product_join = ""
        unit_fuel_vol = "0"
        fuel_rows_expr = "0"
        if fmap["product"]:
            product_join = (
                f" LEFT JOIN PRODUTOS P ON P.ID_PRODUTOS=IC.{fmap['product']}"
                f" AND P.ID_FILIAL=C.ID_FILIAL"
            )
            fuel_rows_expr = f"SUM(CASE WHEN IC.{fmap['product']} IN ({fuel_in}) THEN 1 ELSE 0 END)"
            if fmap["qty"]:
                unit_fuel_vol = (
                    f"SUM(CASE WHEN IC.{fmap['product']} IN ({fuel_in})"
                    f" AND UPPER(ISNULL(P.UNIDADE,'')) IN ('L','LT','LITRO','LITROS','LITER','LITERS')"
                    f" THEN IC.{fmap['qty']} ELSE 0 END)"
                )
                unit_all_vol = (
                    f"SUM(CASE WHEN UPPER(ISNULL(P.UNIDADE,'')) IN ('L','LT','LITRO','LITROS','LITER','LITERS')"
                    f" THEN IC.{fmap['qty']} ELSE 0 END)"
                )
            else:
                unit_all_vol = "0"
        else:
            unit_all_vol = "0"

        cur.execute(
            f"""
            SELECT
              CAST(C.ID_COMPROVANTE AS VARCHAR(50)),
              COUNT(*),
              {fuel_rows_expr},
              {unit_fuel_vol},
              {unit_all_vol},
              CAST(SUM(ISNULL({total_expr},0)) AS DECIMAL(22,4))
            FROM COMPROVANTES C
            INNER JOIN ITENSCOMPROVANTE IC
              ON IC.{fmap['invoice']}=C.ID_COMPROVANTE
              {join_filial}
              {join_db}
            {product_join}
            WHERE C.ID_FILIAL={BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            GROUP BY C.ID_COMPROVANTE
            """
        )
        fis_by_inv: dict[str, dict] = {}
        for r in cur.fetchall():
            fis_by_inv[r[0]] = {
                "items_fiscal_count": int(r[1]),
                "fuel_fiscal_rows": int(r[2] or 0),
                "volume_lt_fuel_fiscal": str(r[3] or 0),
                "volume_lt_fiscal": str(r[4] or 0),
                "total_fiscal": str(r[5] or 0),
            }

        # Totais agregados
        def _sum_dec(rows: list[dict], key: str) -> Decimal:
            return sum((Decimal(str(r.get(key) or 0)) for r in rows), Decimal(0))

        rows = []
        for inv_id, base in sorted(all_invs.items(), key=lambda x: (x[1]["entry_date"], x[0])):
            m = mov_by_inv.get(inv_id, {})
            f = fis_by_inv.get(inv_id, {})
            mov_n = int(m.get("items_mov_count") or 0)
            fis_n = int(f.get("items_fiscal_count") or 0)
            row = {
                **base,
                "items_mov_count": mov_n,
                "items_fiscal_count": fis_n,
                "volume_lt_mov": m.get("volume_lt_mov", "0"),
                "volume_lt_fiscal": f.get("volume_lt_fiscal", "0"),
                "volume_lt_fuel_mov": m.get("volume_lt_fuel_mov", "0"),
                "volume_lt_fuel_fiscal": f.get("volume_lt_fuel_fiscal", "0"),
                "total_mov": m.get("total_mov", "0"),
                "total_fiscal": f.get("total_fiscal", "0"),
                "fuel_mov_rows": m.get("fuel_mov_rows", 0),
                "fuel_fiscal_rows": f.get("fuel_fiscal_rows", 0),
                "movement_only": mov_n > 0 and fis_n == 0,
                "fiscal_only": fis_n > 0 and mov_n == 0,
                "both_sources": mov_n > 0 and fis_n > 0,
                "neither_source": mov_n == 0 and fis_n == 0,
            }
            rows.append(row)

        # Dias candidatos com combustível LT no movimento
        cur.execute(
            f"""
            SELECT CONVERT(varchar(10), C.DTACONTA, 23),
                   COUNT(DISTINCT C.ID_COMPROVANTE),
                   COUNT(*),
                   CAST(SUM(I.QTDE) AS DECIMAL(18,3)),
                   CAST(SUM(CASE WHEN I.VLRCUSTOSEMICMS=0 THEN I.TOTAL ELSE I.QTDE*I.VLRCUSTOSEMICMS END)
                        AS DECIMAL(22,4))
            FROM COMPROVANTES C
            INNER JOIN MOVPRODUTOS M
              ON M.ID_COMPROVANTE=C.ID_COMPROVANTE AND M.ID_FILIAL=C.ID_FILIAL AND M.ID_DB=C.ID_DB
            INNER JOIN ITENSMOVPRODUTOS I
              ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
            INNER JOIN PRODUTOS P ON P.ID_PRODUTOS=I.ID_PRODUTOS AND P.ID_FILIAL=I.ID_FILIAL
            WHERE C.ID_FILIAL={BRANCH}
              AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
              AND I.ID_PRODUTOS IN ({fuel_in})
              AND UPPER(ISNULL(P.UNIDADE,'')) IN ('L','LT','LITRO','LITROS','LITER','LITERS')
              AND I.QTDE > 0
            GROUP BY CONVERT(varchar(10), C.DTACONTA, 23)
            ORDER BY 1
            """
        )
        candidate_days = [
            {
                "day": r[0],
                "invoices_with_fuel_lt": int(r[1]),
                "fuel_lt_rows": int(r[2]),
                "volume_lt": str(r[3]),
                "cost_approx": str(r[4]),
            }
            for r in cur.fetchall()
        ]

        # Produtos de interesse
        product_profile = []
        for pid in list(FUEL_IDS) + list(IGNORE_IDS):
            cur.execute(
                f"""
                SELECT CAST(P.NOMEPRODUTO AS VARCHAR(120)), CAST(P.UNIDADE AS VARCHAR(20))
                FROM PRODUTOS P WHERE P.ID_FILIAL={BRANCH} AND P.ID_PRODUTOS={pid}
                """
            )
            prow = cur.fetchone()
            cur.execute(
                f"""
                SELECT COUNT(*), CAST(SUM(I.QTDE) AS DECIMAL(18,3))
                FROM ITENSMOVPRODUTOS I
                INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
                INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
                WHERE I.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
                  AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
                  AND I.ID_PRODUTOS={pid}
                """
            )
            movp = cur.fetchone()
            fis_count = fis_qty = None
            if fmap["product"] and fmap["qty"]:
                cur.execute(
                    f"""
                    SELECT COUNT(*), CAST(SUM(IC.{fmap['qty']}) AS DECIMAL(18,3))
                    FROM ITENSCOMPROVANTE IC
                    INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=IC.{fmap['invoice']}
                      {join_filial} {join_db}
                    WHERE C.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
                      AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
                      AND IC.{fmap['product']}={pid}
                    """
                )
                fisp = cur.fetchone()
                fis_count, fis_qty = int(fisp[0]), str(fisp[1] or 0)
            product_profile.append(
                {
                    "erp_product_id": str(pid),
                    "name": prow[0] if prow else None,
                    "unit": prow[1] if prow else None,
                    "is_fuel_candidate": pid in FUEL_IDS,
                    "should_ignore": pid in IGNORE_IDS,
                    "mov_rows": int(movp[0]),
                    "mov_qty": str(movp[1] or 0),
                    "fiscal_rows": fis_count,
                    "fiscal_qty": fis_qty,
                }
            )

        summary = {
            "period": {"from": start, "to": date_to.isoformat(), "days": DAYS, "branch": BRANCH},
            "itenscomprovante_column_map": fmap,
            "itenscomprovante_columns": fis_cols,
            "itensmovprodutos_columns_count": len(mov_cols),
            "totals": {
                "invoices": len(all_invs),
                "invoices_with_mov_items": sum(1 for r in rows if r["items_mov_count"] > 0),
                "invoices_with_fiscal_items": sum(1 for r in rows if r["items_fiscal_count"] > 0),
                "movement_only": sum(1 for r in rows if r["movement_only"]),
                "fiscal_only": sum(1 for r in rows if r["fiscal_only"]),
                "both_sources": sum(1 for r in rows if r["both_sources"]),
                "neither_source": sum(1 for r in rows if r["neither_source"]),
                "items_mov": sum(r["items_mov_count"] for r in rows),
                "items_fiscal": sum(r["items_fiscal_count"] for r in rows),
                "volume_lt_mov": str(_sum_dec(rows, "volume_lt_mov")),
                "volume_lt_fiscal": str(_sum_dec(rows, "volume_lt_fiscal")),
                "volume_lt_fuel_mov": str(_sum_dec(rows, "volume_lt_fuel_mov")),
                "volume_lt_fuel_fiscal": str(_sum_dec(rows, "volume_lt_fuel_fiscal")),
                "total_mov": str(_sum_dec(rows, "total_mov")),
                "total_fiscal": str(_sum_dec(rows, "total_fiscal")),
            },
            "candidate_days_fuel_lt_movement": candidate_days,
            "recommended_one_day": (
                min(
                    candidate_days,
                    key=lambda d: (d["invoices_with_fuel_lt"], d["fuel_lt_rows"], d["day"]),
                )["day"]
                if candidate_days
                else None
            ),
            "product_profile": product_profile,
            "rows": rows,
            "note": (
                "Perfil somente leitura. Não altera pipeline. "
                "Não faz UNION das fontes. Matching canônico fica para implementação posterior."
            ),
        }

        stem = f"sprint-08-3-source-profile-{DAYS}d"
        (out_dir / f"{stem}.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        # CSV por nota
        csv_lines = [
            "source_invoice_id,document_number,entry_date,supplier,"
            "items_mov_count,items_fiscal_count,volume_lt_mov,volume_lt_fiscal,"
            "total_mov,total_fiscal,movement_only,fiscal_only,both_sources,neither_source"
        ]
        for r in rows:
            csv_lines.append(
                ",".join(
                    str(r[k])
                    for k in [
                        "source_invoice_id",
                        "document_number",
                        "entry_date",
                        "supplier",
                        "items_mov_count",
                        "items_fiscal_count",
                        "volume_lt_mov",
                        "volume_lt_fiscal",
                        "total_mov",
                        "total_fiscal",
                        "movement_only",
                        "fiscal_only",
                        "both_sources",
                        "neither_source",
                    ]
                )
            )
        (out_dir / f"{stem}.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

        t = summary["totals"]
        md = [
            f"# Sprint 8.3 — Perfil de fontes de itens ({DAYS} dias)",
            "",
            f"Filial `{BRANCH}` · `{start}` → `{date_to.isoformat()}`",
            "",
            "## Totais",
            "",
            "| Métrica | ITENSMOVPRODUTOS | ITENSCOMPROVANTE |",
            "|---------|------------------|------------------|",
            f"| Notas com itens | {t['invoices_with_mov_items']} | {t['invoices_with_fiscal_items']} |",
            f"| Total de itens | {t['items_mov']} | {t['items_fiscal']} |",
            f"| Volume LT (todas unidades L*) | {t['volume_lt_mov']} | {t['volume_lt_fiscal']} |",
            f"| Volume LT combustível (1/2/4/1271/1272) | {t['volume_lt_fuel_mov']} | {t['volume_lt_fuel_fiscal']} |",
            f"| Valor itens | {t['total_mov']} | {t['total_fiscal']} |",
            "",
            f"Notas totais: **{t['invoices']}**",
            f"Somente movimento: **{t['movement_only']}** · Somente fiscal: **{t['fiscal_only']}** · Ambas: **{t['both_sources']}** · Nenhuma: **{t['neither_source']}**",
            "",
            "## Dias candidatos (combustível LT no movimento)",
            "",
        ]
        if not candidate_days:
            md.append("Nenhum dia com combustível LT em ITENSMOVPRODUTOS no período.")
        else:
            md.append("| Dia | Notas | Linhas | Volume LT | Custo ~ |")
            md.append("|-----|-------|--------|-----------|---------|")
            for d in candidate_days:
                md.append(
                    f"| {d['day']} | {d['invoices_with_fuel_lt']} | {d['fuel_lt_rows']} | "
                    f"{d['volume_lt']} | {d['cost_approx']} |"
                )
            md.append("")
            md.append(f"**Dia recomendado (menor primeiro na lista):** `{summary['recommended_one_day']}`")
        md.extend(["", "## Mapa de colunas ITENSCOMPROVANTE", "", "```json", json.dumps(fmap, indent=2), "```", ""])
        (out_dir / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

        print(
            json.dumps(
                {
                    "days": DAYS,
                    "totals": t,
                    "recommended_one_day": summary["recommended_one_day"],
                    "candidate_days": candidate_days,
                    "fiscal_column_map": fmap,
                    "wrote": stem,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    finally:
        ds.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
