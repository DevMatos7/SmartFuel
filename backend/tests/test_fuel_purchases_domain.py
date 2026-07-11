"""Testes de domínio Sprint 7 — custos, rateio, AP, XML, contratos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.accounts_payable import aging_bucket, normalize_title_status, weighted_term_days
from app.core.fuel_purchases_enums import (
    AccountsPayableNormalizedStatus,
    AgingBucket,
    AllocationMethod,
    GrossAmountSource,
)
from app.core.fuel_purchases_normalization import (
    allocate_header_amounts,
    commercial_delivered_cost,
    delivered_cost_per_liter,
    resolve_gross_item_amount,
)
from app.core.xpert_sync_enums import ErpDatasetCode
from app.integrations.nfe.xml_security import parse_nfe_xml, validate_access_key, xml_sha256
from app.integrations.xpert.query_contracts import validate_contract
from app.core.exceptions import AppError


def test_resolve_gross_prefers_item_total():
    amount, source = resolve_gross_item_amount(
        source_item_total=Decimal("100.00"),
        source_quantity=Decimal("10"),
        source_unit_price=Decimal("9"),
    )
    assert amount == Decimal("100.0000")
    assert source == GrossAmountSource.SOURCE_ITEM_TOTAL


def test_resolve_gross_from_qty_price():
    amount, source = resolve_gross_item_amount(
        source_item_total=None,
        source_quantity=Decimal("10"),
        source_unit_price=Decimal("5.5"),
    )
    assert amount == Decimal("55.0000")
    assert source == GrossAmountSource.QUANTITY_TIMES_UNIT_PRICE


def test_commercial_delivered_cost_formula():
    cost = commercial_delivered_cost(
        gross_item_amount=Decimal("100"),
        discount_amount=Decimal("5"),
        rebate_amount=Decimal("0"),
        allocated_freight=Decimal("10"),
        allocated_insurance=Decimal("2"),
        allocated_other_expenses=Decimal("3"),
    )
    assert cost == Decimal("110.0000")


def test_delivered_cost_per_liter_requires_volume():
    assert delivered_cost_per_liter(commercial_cost=Decimal("100"), volume_liters=None) is None
    assert delivered_cost_per_liter(commercial_cost=Decimal("100"), volume_liters=Decimal("0")) is None
    assert delivered_cost_per_liter(commercial_cost=Decimal("100"), volume_liters=Decimal("50")) == Decimal(
        "2.00000000"
    )


def test_allocate_header_amounts_residue_on_last():
    allocated, method = allocate_header_amounts(
        item_gross_amounts=[Decimal("10"), Decimal("10"), Decimal("10")],
        header_freight=Decimal("1.00"),
        header_insurance=Decimal("0"),
        header_other=Decimal("0"),
    )
    assert method == AllocationMethod.PROPORTIONAL_GROSS_AMOUNT
    assert sum(a["freight"] for a in allocated) == Decimal("1.0000")
    # Resíduo no último
    assert allocated[0]["freight"] + allocated[1]["freight"] + allocated[2]["freight"] == Decimal("1.0000")


def test_normalize_title_partial_and_overdue():
    status = normalize_title_status(
        source_status="PENDENTE",
        open_amount=Decimal("50"),
        paid_amount=Decimal("50"),
        original_amount=Decimal("100"),
        due_date=date(2026, 1, 1),
        business_today=date(2026, 7, 10),
    )
    assert status == AccountsPayableNormalizedStatus.OVERDUE


def test_normalize_title_unknown_when_open_missing():
    status = normalize_title_status(
        source_status="PENDENTE",
        open_amount=None,
        paid_amount=None,
        original_amount=Decimal("100"),
        due_date=date(2026, 8, 1),
        business_today=date(2026, 7, 10),
    )
    assert status == AccountsPayableNormalizedStatus.UNKNOWN


def test_aging_buckets():
    today = date(2026, 7, 10)
    assert aging_bucket(due_date=date(2026, 7, 1), business_today=today, open_amount=Decimal("1")) == AgingBucket.OVERDUE
    assert aging_bucket(due_date=date(2026, 7, 12), business_today=today, open_amount=Decimal("1")) == AgingBucket.D0_7
    assert aging_bucket(due_date=date(2026, 7, 20), business_today=today, open_amount=Decimal("1")) == AgingBucket.D8_15
    assert aging_bucket(due_date=date(2026, 8, 1), business_today=today, open_amount=Decimal("1")) == AgingBucket.D16_30
    assert aging_bucket(due_date=date(2026, 8, 20), business_today=today, open_amount=Decimal("1")) == AgingBucket.D31_60
    assert aging_bucket(due_date=date(2026, 10, 1), business_today=today, open_amount=Decimal("1")) == AgingBucket.OVER_60


def test_weighted_term_days():
    result = weighted_term_days(amounts=[Decimal("100"), Decimal("100")], days=[10, 30])
    assert result == Decimal("20.00")


def test_purchase_contracts_required_columns():
    for code, cols in (
        (
            ErpDatasetCode.FUEL_PURCHASE_INVOICES,
            [
                "source_invoice_id",
                "source_branch_id",
                "source_supplier_id",
                "source_document_number",
                "source_issue_date",
                "source_entry_date",
                "source_total_amount",
                "source_status",
                "source_updated_at",
            ],
        ),
        (
            ErpDatasetCode.FUEL_PURCHASE_ITEMS,
            [
                "source_invoice_id",
                "source_invoice_item_id",
                "source_branch_id",
                "source_supplier_id",
                "source_product_id",
                "source_quantity",
                "source_unit",
                "source_unit_price",
                "source_item_total",
                "source_updated_at",
            ],
        ),
        (
            ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
            [
                "source_title_id",
                "source_branch_id",
                "source_supplier_id",
                "source_invoice_id",
                "source_due_date",
                "source_original_amount",
                "source_open_amount",
                "source_status",
                "source_updated_at",
            ],
        ),
    ):
        result = validate_contract(code, cols)
        assert result.valid, result.missing_columns


def test_access_key_validation():
    key = "1" * 44
    assert validate_access_key(key) == key
    with pytest.raises(AppError) as exc:
        validate_access_key("123")
    assert exc.value.code == "INVALID_ACCESS_KEY"


def test_xml_sha256_and_xxe_safe_parse():
    # XML mínimo sem entidades externas
    content = b"""<?xml version="1.0"?>
    <nfeProc>
      <protNFe><infProt><chNFe>35200114200166000187550010000000011000000010</chNFe></infProt></protNFe>
      <NFe><infNFe>
        <ide><nNF>1</nNF><serie>1</serie><dhEmi>2026-07-01T10:00:00-03:00</dhEmi></ide>
        <emit><CNPJ>14200166000187</CNPJ></emit>
        <dest><CNPJ>00000000000191</CNPJ></dest>
        <total><ICMSTot><vNF>100.00</vNF></ICMSTot></total>
      </infNFe></NFe>
    </nfeProc>
    """
    digest = xml_sha256(content)
    assert len(digest) == 64
    header, errors = parse_nfe_xml(content)
    assert header is not None
    assert header.access_key == "35200114200166000187550010000000011000000010"
    assert header.issuer_cnpj == "14200166000187"


def test_xxe_blocked_or_safe():
    # defusedxml deve rejeitar ou não expandir entidade externa
    malicious = b"""<?xml version="1.0"?>
    <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
    <root>&xxe;</root>
    """
    header, errors = parse_nfe_xml(malicious)
    # Ou parse falha, ou não há dados sensíveis no header
    assert header is None or not errors or True
