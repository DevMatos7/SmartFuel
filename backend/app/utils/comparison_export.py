from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.models.quote_comparison_run import QuoteComparisonResult, QuoteComparisonRun


def _distributor_label(result: QuoteComparisonResult) -> str:
    if isinstance(result.input_snapshot, dict):
        name = result.input_snapshot.get("distributor_name")
        if name:
            return str(name)
    return str(result.distributor_id)


def _quote_number(result: QuoteComparisonResult) -> str:
    if isinstance(result.input_snapshot, dict) and result.input_snapshot.get("quote_number") is not None:
        return str(result.input_snapshot["quote_number"])
    return ""


def build_comparison_csv(run: QuoteComparisonRun) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "rank_position",
            "distributor_name",
            "quote_number",
            "quote_id",
            "quote_item_id",
            "eligibility_status",
            "raw_price_per_liter",
            "delivered_cost_per_liter",
            "financial_equivalent_cost_per_liter",
            "ranking_cost_per_liter",
            "difference_per_liter",
            "difference_total",
            "calculation_hash",
        ]
    )
    for result in run.results:
        writer.writerow(
            [
                result.rank_position or "",
                _distributor_label(result),
                _quote_number(result),
                str(result.quote_id),
                str(result.quote_item_id),
                result.eligibility_status,
                str(result.raw_price_per_liter),
                str(result.delivered_cost_per_liter),
                str(result.financial_equivalent_cost_per_liter or ""),
                str(result.ranking_cost_per_liter or ""),
                str(result.difference_per_liter or ""),
                str(result.difference_total or ""),
                run.calculation_hash or "",
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")


def build_comparison_pdf(run: QuoteComparisonRun, *, generated_by: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    def line(text: str, *, bold: bool = False) -> None:
        nonlocal y
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        pdf.drawString(2 * cm, y, text[:110])
        y -= 0.55 * cm

    financial = (run.input_snapshot or {}).get("financial_parameter") or {}
    line("Comparação de Cotações", bold=True)
    line(f"Execução: {run.id}")
    line(f"Modo: {run.ranking_mode} | Escopo: {run.ranking_scope}")
    line(f"Volume: {run.requested_volume_liters} L")
    line(f"Comparação em: {run.comparison_datetime.isoformat()}")
    line(f"Metodologia: {run.methodology_version}")
    if financial.get("annual_effective_rate"):
        line(f"Taxa anual: {financial['annual_effective_rate']}")
    if run.calculation_hash:
        line(f"Hash: {run.calculation_hash}")
    line("")
    line("Indicadores", bold=True)
    line(
        f"Elegíveis: {run.eligible_count} | Alertas: {run.warning_count} | "
        f"Inelegíveis: {run.ineligible_count}"
    )
    if run.best_cost_per_liter is not None:
        line(f"Melhor custo: R$ {run.best_cost_per_liter}/L")
    if run.spread_absolute is not None:
        line(f"Spread: R$ {run.spread_absolute}/L ({run.spread_percent}%)")
    line("")
    line("Ranking", bold=True)
    ranked = sorted(
        [r for r in run.results if r.rank_position is not None],
        key=lambda r: r.rank_position or 999,
    )
    for result in ranked:
        line(
            f"#{result.rank_position} {_distributor_label(result)} | "
            f"entregue {result.delivered_cost_per_liter} | "
            f"equiv {result.financial_equivalent_cost_per_liter or '-'} | "
            f"{result.eligibility_status}"
        )
    line("")
    line("Propostas fora do ranking", bold=True)
    for result in [r for r in run.results if r.rank_position is None]:
        reasons = ", ".join(reason.get("code", "") for reason in (result.eligibility_reasons or []))
        line(f"{_distributor_label(result)} | {result.eligibility_status} | {reasons}")
    line("")
    line(f"Gerado em {datetime.now(UTC).isoformat()} por {generated_by}")
    pdf.save()
    buffer.seek(0)
    return buffer.read()
