"""Sprint 8.1 — matriz de descoberta de comparabilidade (somente leitura).

Uso:
  python scripts/homolog_sprint81_discovery.py [days=30] [station_id?]
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.purchase_benchmark_enums import PurchaseReferenceConfidence, PurchaseReferenceSource
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.product import Product
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.services.purchase_benchmark_support import (
    ActualPurchaseCostService,
    PurchaseBenchmarkReferenceService,
    PurchaseItemGroupingService,
)
from app.services.quote_eligibility_service import ComparisonScenario
from app.services.quote_evaluation_service import QuoteEvaluationService
from app.core.quote_comparison_enums import EligibilityStatus, RankingMode

VALID_FUEL_FAMILIES = {"ETHANOL", "GASOLINE_C", "DIESEL_B_S10", "DIESEL_B_S500"}
VALID_LITER_UNITS = {"L", "LT", "LITER", "LITERS", "LITRO", "LITROS"}

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
STATION_FILTER = uuid.UUID(sys.argv[2]) if len(sys.argv) > 2 else None


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


OUT_DIR = _out_dir()
OUT_JSON = OUT_DIR / f"sprint-08-1-discovery-{DAYS}d.json"
OUT_MD = OUT_DIR / f"sprint-08-1-discovery-{DAYS}d.md"


def _is_fuel(product: Product | None) -> bool:
    if product is None:
        return False
    return (
        product.fuel_family in VALID_FUEL_FAMILIES
        and (product.unit or "").upper() in VALID_LITER_UNITS
    )


async def main() -> None:
    date_to = date.today()
    date_from = date_to - timedelta(days=DAYS)
    rows_out: list[dict] = []
    reasons = Counter()

    async with AsyncSessionLocal() as db:
        # Cobertura efetivamente carregada no PG (independente da janela pesquisada)
        cov_q = select(FuelPurchaseInvoice)
        if STATION_FILTER:
            cov_q = cov_q.where(FuelPurchaseInvoice.station_id == STATION_FILTER)
        all_inv = list((await db.execute(cov_q)).scalars().all())
        pg_days = sorted({i.entry_date for i in all_inv})
        pg_coverage = {
            "searched_period": {"from": date_from.isoformat(), "to": date_to.isoformat(), "days": DAYS},
            "first_purchase_day_pg": pg_days[0].isoformat() if pg_days else None,
            "last_purchase_day_pg": pg_days[-1].isoformat() if pg_days else None,
            "days_with_purchases_pg": len(pg_days),
            "invoices_pg_all": len(all_inv),
            "interpretation": (
                "A janela pesquisada NÃO implica que o PG contenha compras em todos esses dias. "
                "REAL_COMPARABLE_PURCHASES refere-se apenas aos dados disponíveis no PostgreSQL."
            ),
        }

        inv_q = (
            select(FuelPurchaseInvoice)
            .where(
                FuelPurchaseInvoice.is_cancelled.is_(False),
                FuelPurchaseInvoice.operation_type != "PURCHASE_RETURN",
                FuelPurchaseInvoice.entry_date >= date_from,
                FuelPurchaseInvoice.entry_date <= date_to,
            )
            .order_by(FuelPurchaseInvoice.entry_date.desc())
        )
        if STATION_FILTER:
            inv_q = inv_q.where(FuelPurchaseInvoice.station_id == STATION_FILTER)
        invoices = list((await db.execute(inv_q)).scalars().all())

        ref_svc = PurchaseBenchmarkReferenceService(db)
        group_svc = PurchaseItemGroupingService()
        eval_svc = QuoteEvaluationService(db)

        for inv in invoices:
            items = list(
                (
                    await db.execute(
                        select(FuelPurchaseItem).where(
                            FuelPurchaseItem.purchase_invoice_id == inv.id,
                            FuelPurchaseItem.is_cancelled.is_(False),
                        )
                    )
                ).scalars().all()
            )
            if not items:
                continue
            reference = await ref_svc.resolve(invoice=inv, organization_id=inv.organization_id)
            groups = group_svc.group(items)

            for group in groups:
                product = None
                if group.canonical_product_id:
                    product = (
                        await db.execute(select(Product).where(Product.id == group.canonical_product_id))
                    ).scalar_one_or_none()

                per_l = ActualPurchaseCostService.cost_per_liter(
                    total_cost=group.commercial_delivered_cost, volume_liters=group.volume_liters
                )
                reason = None
                quotes_before = 0
                eligible = 0
                best_cost = None

                if group.unmapped or group.canonical_product_id is None:
                    reason = "UNMAPPED_PRODUCT"
                elif not _is_fuel(product):
                    reason = "NOT_FUEL_PRODUCT"
                elif group.volume_liters is None or group.volume_liters <= 0:
                    reason = "MISSING_VOLUME"
                elif per_l is None:
                    reason = "MISSING_ACTUAL_COST"
                elif reference.reference_datetime is None:
                    reason = "REFERENCE_TIME_UNAVAILABLE"
                else:
                    # contagem histórica (SQL) — conhecidas em T
                    T = reference.reference_datetime
                    q_count = (
                        await db.execute(
                            select(func.count())
                            .select_from(QuoteItem)
                            .join(Quote, Quote.id == QuoteItem.quote_id)
                            .where(
                                Quote.organization_id == inv.organization_id,
                                Quote.station_id == inv.station_id,
                                QuoteItem.product_id == group.canonical_product_id,
                                Quote.activated_at.isnot(None),
                                Quote.activated_at <= T,
                                or_(Quote.cancelled_at.is_(None), Quote.cancelled_at > T),
                                or_(Quote.superseded_at.is_(None), Quote.superseded_at > T),
                                Quote.valid_until > T,
                            )
                        )
                    ).scalar_one()
                    quotes_before = int(q_count)

                    if quotes_before == 0:
                        reason = "NO_QUOTES_AVAILABLE"
                    else:
                        scenario = ComparisonScenario(
                            organization_id=inv.organization_id,
                            station_id=inv.station_id,
                            product_id=group.canonical_product_id,
                            requested_volume_liters=group.volume_liters,
                            comparison_datetime=T,
                            required_delivery_at=None,
                            ranking_mode=RankingMode.DELIVERED,
                        )
                        batch = await eval_svc.evaluate_batch(
                            organization_id=inv.organization_id,
                            scenario=scenario,
                            financial_parameter=None,
                        )
                        elig = [
                            c
                            for c in batch.contexts
                            if c.eligibility_status
                            in {EligibilityStatus.ELIGIBLE, EligibilityStatus.ELIGIBLE_WITH_WARNINGS}
                        ]
                        eligible = len(elig)
                        if eligible == 0:
                            reason = "NO_ELIGIBLE_QUOTES"
                        else:
                            best_cost = str(
                                min(c.costs.delivered_cost_per_liter for c in elig)
                            )

                if reason:
                    reasons[reason] += 1
                else:
                    reasons["COMPARABLE"] += 1
                if reference.confidence == PurchaseReferenceConfidence.LOW:
                    reasons["LOW_CONFIDENCE_REF"] += 1

                rows_out.append(
                    {
                        "purchase_invoice_id": str(inv.id),
                        "document_number": inv.source_document_number,
                        "station_id": str(inv.station_id),
                        "entry_date": inv.entry_date.isoformat(),
                        "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                        "reference_datetime": reference.reference_datetime.isoformat()
                        if reference.reference_datetime
                        else None,
                        "reference_source": reference.source,
                        "reference_confidence": reference.confidence,
                        "canonical_product_id": str(group.canonical_product_id)
                        if group.canonical_product_id
                        else None,
                        "product_name": product.name if product else None,
                        "fuel_family": product.fuel_family if product else None,
                        "volume_liters": str(group.volume_liters),
                        "actual_cost_total": str(group.commercial_delivered_cost),
                        "actual_cost_per_liter": str(per_l) if per_l is not None else None,
                        "actual_distributor_id": str(inv.distributor_id) if inv.distributor_id else None,
                        "quotes_before_T": quotes_before,
                        "eligible_candidates": eligible,
                        "best_delivered_cost_per_liter": best_cost,
                        "non_comparability_reason": reason,
                        "group_key": group.group_key,
                        "item_count": len(group.item_ids),
                    }
                )

    comparable = [r for r in rows_out if r["non_comparability_reason"] is None]
    summary = {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat(), "days": DAYS},
        "station_filter": str(STATION_FILTER) if STATION_FILTER else None,
        "pg_loaded_coverage": pg_coverage,
        "groups_analyzed": len(rows_out),
        "technically_comparable": len(comparable),
        "REAL_COMPARABLE_PURCHASES": len(comparable),
        "REAL_COMPARABLE_PURCHASES_SCOPE": "available_postgres_data_only",
        "reason_counts": dict(reasons),
        "comparable_sample": comparable[:20],
        "rows": rows_out,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# Sprint 8.1 — Descoberta de comparabilidade ({DAYS} dias)",
        "",
        f"## Período pesquisado vs cobertura no PG",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Período pesquisado | `{date_from}` → `{date_to}` ({DAYS}d) |",
        f"| Primeiro dia de compra no PG | {pg_coverage['first_purchase_day_pg']} |",
        f"| Último dia de compra no PG | {pg_coverage['last_purchase_day_pg']} |",
        f"| Dias com compras no PG | {pg_coverage['days_with_purchases_pg']} |",
        f"| Notas no PG (todas) | {pg_coverage['invoices_pg_all']} |",
        "",
        f"> {pg_coverage['interpretation']}",
        "",
        f"Grupos analisados na janela (nota×produto): **{len(rows_out)}**",
        f"Tecnicamente comparáveis (nos dados do PG): **{len(comparable)}**",
        f"`REAL_COMPARABLE_PURCHASES = {len(comparable)}` (escopo: PostgreSQL disponível)",
        "",
        "## Motivos",
        "",
        "| Motivo | Qtd |",
        "|--------|-----|",
    ]
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines.extend(["", "## Comparáveis (amostra)", ""])
    if not comparable:
        lines.append("Nenhuma compra comparável no período. Homologação real bloqueada por dados.")
    else:
        lines.append(
            "| Nota | Posto | Ref | Conf | Produto | Vol | Real/L | Cotações | Elegíveis | Melhor/L |"
        )
        lines.append("|------|-------|-----|------|---------|-----|--------|----------|-----------|----------|")
        for r in comparable[:30]:
            lines.append(
                f"| {r['document_number']} | `{r['station_id'][:8]}…` | {r['reference_datetime']} | "
                f"{r['reference_confidence']} | {r['product_name'] or r['canonical_product_id']} | "
                f"{r['volume_liters']} | {r['actual_cost_per_liter']} | {r['quotes_before_T']} | "
                f"{r['eligible_candidates']} | {r['best_delivered_cost_per_liter']} |"
            )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "rows"}, indent=2))
    print("wrote", OUT_JSON, OUT_MD)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
