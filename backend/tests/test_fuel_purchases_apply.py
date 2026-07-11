"""Testes Sprint 7.1 — apply, waiting, títulos, rateio, agregação."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.fuel_purchases_enums import InvoiceLinkStatus, PurchaseMetricEligibilityStatus
from app.core.fuel_purchases_normalization import allocate_header_amounts
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus
from app.services.fuel_purchases_apply_service import FuelPurchasesApplyService


def test_allocate_residue_closes_exactly():
    allocated, method = allocate_header_amounts(
        item_gross_amounts=[Decimal("10.00"), Decimal("20.00"), Decimal("30.00")],
        header_freight=Decimal("1.00"),
    )
    assert method.value == "PROPORTIONAL_GROSS_AMOUNT"
    assert sum(a["freight"] for a in allocated) == Decimal("1.0000")


@pytest.mark.asyncio
async def test_item_waits_when_invoice_missing():
    db = AsyncMock()
    service = FuelPurchasesApplyService(db)
    run = MagicMock()
    run.organization_id = uuid4()
    run.station_id = uuid4()
    run.id = uuid4()

    station = MagicMock()
    station.erp_branch_id = "2443"
    # branch guard + load invoice None
    async def execute_side_effect(stmt):
        result = MagicMock()
        # First call station, second invoice
        if not hasattr(execute_side_effect, "n"):
            execute_side_effect.n = 0
        execute_side_effect.n += 1
        if execute_side_effect.n == 1:
            result.scalar_one_or_none.return_value = station
        else:
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)

    staging = MagicMock()
    staging.dataset_code = ErpDatasetCode.FUEL_PURCHASE_ITEMS
    staging.normalized_payload = {
        "source_invoice_id": "1",
        "source_invoice_item_id": "2",
        "source_branch_id": "2443",
        "source_product_id": "10",
        "source_quantity": "1",
        "source_unit": "L",
        "source_unit_price": "1",
        "source_item_total": "1",
        "source_updated_at": datetime.now(UTC),
    }
    staging.record_hash = "abc"

    outcome = await service._apply_item(run=run, staging=staging, now=datetime.now(UTC))
    assert outcome == "waiting_for_invoice"
    assert staging.processing_status == ErpStagingStatus.WAITING_FOR_INVOICE


def test_title_link_status_enum():
    assert InvoiceLinkStatus.PENDING_INVOICE_LINK.value == "PENDING_INVOICE_LINK"
    assert PurchaseMetricEligibilityStatus.ELIGIBLE.value == "ELIGIBLE"
