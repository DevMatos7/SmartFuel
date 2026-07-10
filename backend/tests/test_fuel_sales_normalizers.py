"""Testes de normalização Sprint 6."""

from app.core.xpert_sync_enums import ErpDatasetCode
from app.integrations.xpert.normalizers import hash_payload_for_dataset, normalize_row, source_key_for_row


def test_normalize_payment_method_row():
    row = normalize_row(
        ErpDatasetCode.PAYMENT_METHODS,
        {
            "source_payment_method_id": "4",
            "source_payment_method_code": "DEB",
            "source_payment_method_name": "Cartão Débito",
            "source_active": 1,
        },
    )
    assert row["source_payment_method_id"] == "4"
    assert row["source_payment_method_name"] == "Cartão Débito"
    assert row["source_active"] is True
    assert source_key_for_row(ErpDatasetCode.PAYMENT_METHODS, row) == "4"


def test_normalize_fuel_sales_item_row():
    row = normalize_row(
        ErpDatasetCode.FUEL_SALES_ITEMS,
        {
            "source_sale_id": "100",
            "source_sale_item_id": "1",
            "source_branch_id": "2443",
            "source_sale_datetime": "2026-01-15T10:00:00",
            "source_business_date": "2026-01-15",
            "source_product_id": "501",
            "source_quantity": "100.5",
            "source_net_amount": "550.25",
            "source_updated_at": "2026-01-15T11:00:00",
            "source_cancelled": 0,
            "source_unit": "L",
        },
    )
    assert row["source_sale_id"] == "100"
    assert row["source_operation_type"] == "SALE"
    assert source_key_for_row(ErpDatasetCode.FUEL_SALES_ITEMS, row) == "100:1"
    payload = hash_payload_for_dataset(ErpDatasetCode.FUEL_SALES_ITEMS, row)
    assert payload["source_sale_id"] == "100"


def test_normalize_fuel_retail_price_row():
    row = normalize_row(
        ErpDatasetCode.FUEL_RETAIL_PRICES,
        {
            "source_branch_id": "2443",
            "source_product_id": "501",
            "source_payment_method_id": "0",
            "source_price_per_liter": "5.499",
            "source_active": 1,
        },
    )
    assert row["source_price_per_liter"] == "5.499"
    key = source_key_for_row(ErpDatasetCode.FUEL_RETAIL_PRICES, row)
    assert key == "2443:501:0"
