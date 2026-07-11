from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def build_fuel_sales_pdf(
    *,
    title: str,
    generated_by: str,
    period_label: str,
    rows: list[dict],
    include_margin: bool,
) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    def line(text: str, *, bold: bool = False, size: int = 10) -> None:
        nonlocal y
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(2 * cm, y, text[:110])
        y -= 0.55 * cm

    line(title, bold=True, size=14)
    line(f"Período: {period_label}")
    line(f"Gerado por: {generated_by}")
    line("")
    headers = ["Produto", "Volume", "Receita", "Preço médio"]
    if include_margin:
        headers.extend(["Margem", "Margem/L", "Margem %"])
    line(" | ".join(headers), bold=True)

    for row in rows[:80]:
        cells = [
            str(row.get("product_name", "")),
            _fmt(row.get("net_volume_liters")),
            _fmt(row.get("net_sales_amount")),
            _fmt(row.get("realized_price_per_liter")),
        ]
        if include_margin:
            cells.extend(
                [
                    _fmt(row.get("gross_margin_amount")),
                    _fmt(row.get("gross_margin_per_liter")),
                    _fmt(row.get("gross_margin_percent")),
                ]
            )
        line(" | ".join(cells))

    pdf.save()
    return buffer.getvalue()


def _fmt(value: Decimal | str | None) -> str:
    if value is None:
        return "—"
    return str(value)
