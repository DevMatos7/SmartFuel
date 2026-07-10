from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.models.quote import Quote


def build_quote_pdf(quote: Quote, *, generated_by: str) -> bytes:
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

    line(f"Cotação #{quote.quote_number:06d}", bold=True)
    line(f"Status: {quote.status}")
    line(f"Posto: {quote.station_id}")
    line(f"Distribuidora: {quote.distributor_id}")
    if quote.distribution_base_id:
        line(f"Base: {quote.distribution_base_id}")
    line(f"Data: {quote.quoted_at.isoformat()}")
    line(f"Validade: {quote.valid_until.isoformat()}")
    line(f"Canal: {quote.source_channel}")
    line("")
    line("Itens", bold=True)
    for item in sorted(quote.items, key=lambda i: i.sequence):
        line(
            f"- Produto {item.product_id} | R$ {item.quoted_price_per_liter}/L | "
            f"{item.payment_term_name_snapshot} | mín {item.minimum_volume_liters} L"
        )
    line("")
    line("Evidências", bold=True)
    for evidence in quote.evidences:
        if evidence.active:
            line(f"- {evidence.original_file_name} ({evidence.category})")
    line("")
    line(f"Gerado em {datetime.now(UTC).isoformat()} por {generated_by}")
    pdf.save()
    buffer.seek(0)
    return buffer.read()
