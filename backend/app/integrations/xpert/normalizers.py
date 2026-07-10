from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.xpert_sync_enums import ErpDatasetCode
from app.utils.brazilian_document import classify_supplier_document
from app.utils.cnpj import normalize_cnpj


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def json_safe(value: Any) -> Any:
    """Converte valores do pyodbc para tipos serializáveis em JSONB."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return str(value)


def normalize_row(dataset_code: str, row: dict[str, Any]) -> dict[str, Any]:
    lowered = {str(k).lower(): v for k, v in row.items()}

    if dataset_code == ErpDatasetCode.PRODUCTS:
        return {
            "erp_product_id": _clean_str(lowered.get("source_product_id")),
            "erp_product_code": _clean_str(lowered.get("source_product_code")),
            "erp_description": _clean_str(lowered.get("source_description")),
            "erp_unit": _clean_str(lowered.get("source_unit")),
            "erp_group_id": _clean_str(lowered.get("source_group_id")),
            "erp_group_name": _clean_str(lowered.get("source_group_name")),
            "erp_subgroup_id": _clean_str(lowered.get("source_subgroup_id")),
            "erp_subgroup_name": _clean_str(lowered.get("source_subgroup_name")),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
            "source_active": _to_bool(lowered.get("source_active"), default=True),
        }

    if dataset_code == ErpDatasetCode.SUPPLIERS:
        raw_cnpj = _clean_str(lowered.get("source_cnpj"))
        document = classify_supplier_document(raw_cnpj)
        updated_at = parse_source_datetime(lowered.get("source_updated_at"))
        return {
            "erp_entity_id": _clean_str(lowered.get("source_supplier_id")),
            "erp_entity_code": _clean_str(lowered.get("source_supplier_code")),
            "erp_name": _clean_str(lowered.get("source_name")),
            "erp_cnpj": document.cnpj,
            "erp_cpf": document.cpf,
            "erp_document_type": document.document_type.value,
            "document_diagnostic": document.diagnostic.value if document.diagnostic else None,
            "source_cnpj_raw": raw_cnpj,
            "source_updated_at": updated_at.isoformat() if updated_at else None,
            "source_active": _to_bool(lowered.get("source_active"), default=True),
        }

    if dataset_code == ErpDatasetCode.STATIONS:
        return {
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_trade_name": _clean_str(lowered.get("source_trade_name")),
            "source_cnpj": normalize_cnpj(_clean_str(lowered.get("source_cnpj")) or "") or None,
            "source_active": _to_bool(lowered.get("source_active"), default=True),
        }

    if dataset_code == ErpDatasetCode.PAYMENT_METHODS:
        return {
            "source_payment_method_id": _clean_str(lowered.get("source_payment_method_id")),
            "source_payment_method_code": _clean_str(lowered.get("source_payment_method_code")),
            "source_payment_method_name": _clean_str(lowered.get("source_payment_method_name")),
            "source_active": _to_bool(lowered.get("source_active"), default=True),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
        }

    if dataset_code == ErpDatasetCode.FUEL_SALES_ITEMS:
        return {
            "source_sale_id": _clean_str(lowered.get("source_sale_id")),
            "source_sale_item_id": _clean_str(lowered.get("source_sale_item_id")),
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_sale_datetime": parse_source_datetime(lowered.get("source_sale_datetime")),
            "source_business_date": lowered.get("source_business_date"),
            "source_product_id": _clean_str(lowered.get("source_product_id")),
            "source_quantity": lowered.get("source_quantity"),
            "source_net_amount": lowered.get("source_net_amount"),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
            "source_cancelled": _to_bool(lowered.get("source_cancelled"), default=False),
            "source_document_number": _clean_str(lowered.get("source_document_number")),
            "source_unit": _clean_str(lowered.get("source_unit")),
            "source_unit_price": lowered.get("source_unit_price"),
            "source_gross_amount": lowered.get("source_gross_amount"),
            "source_discount_amount": lowered.get("source_discount_amount"),
            "source_surcharge_amount": lowered.get("source_surcharge_amount"),
            "source_cost_per_unit": lowered.get("source_cost_per_unit"),
            "source_total_cost": lowered.get("source_total_cost"),
            "source_payment_method_id": _clean_str(lowered.get("source_payment_method_id")),
            "source_operation_type": _clean_str(lowered.get("source_operation_type")) or "SALE",
        }

    if dataset_code == ErpDatasetCode.FUEL_RETAIL_PRICES:
        return {
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_product_id": _clean_str(lowered.get("source_product_id")),
            "source_payment_method_id": _clean_str(lowered.get("source_payment_method_id")),
            "source_price_per_liter": lowered.get("source_price_per_liter"),
            "source_active": _to_bool(lowered.get("source_active"), default=True),
            "source_effective_from": parse_source_datetime(lowered.get("source_effective_from")),
            "source_effective_until": parse_source_datetime(lowered.get("source_effective_until")),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
        }

    return dict(row)


def source_key_for_row(dataset_code: str, normalized: dict[str, Any]) -> str:
    if dataset_code == ErpDatasetCode.PRODUCTS:
        return normalized["erp_product_id"]
    if dataset_code == ErpDatasetCode.SUPPLIERS:
        return normalized["erp_entity_id"]
    if dataset_code == ErpDatasetCode.STATIONS:
        return normalized["source_branch_id"]
    if dataset_code == ErpDatasetCode.PAYMENT_METHODS:
        return normalized["source_payment_method_id"]
    if dataset_code == ErpDatasetCode.FUEL_SALES_ITEMS:
        return f"{normalized['source_sale_id']}:{normalized['source_sale_item_id']}"
    if dataset_code == ErpDatasetCode.FUEL_RETAIL_PRICES:
        return (
            f"{normalized['source_branch_id']}:"
            f"{normalized['source_product_id']}:"
            f"{normalized['source_payment_method_id']}"
        )
    raise ValueError(f"Unknown dataset: {dataset_code}")


def hash_payload_for_dataset(dataset_code: str, normalized: dict[str, Any]) -> dict[str, Any]:
    if dataset_code == ErpDatasetCode.PRODUCTS:
        return {
            k: normalized.get(k)
            for k in (
                "erp_product_id",
                "erp_product_code",
                "erp_description",
                "erp_unit",
                "erp_group_id",
                "erp_group_name",
                "erp_subgroup_id",
                "erp_subgroup_name",
                "source_active",
            )
        }
    if dataset_code == ErpDatasetCode.SUPPLIERS:
        return {
            k: normalized.get(k)
            for k in (
                "erp_entity_id",
                "erp_entity_code",
                "erp_name",
                "erp_cnpj",
                "erp_cpf",
                "erp_document_type",
                "source_active",
            )
        }
    if dataset_code == ErpDatasetCode.PAYMENT_METHODS:
        return {
            k: normalized.get(k)
            for k in (
                "source_payment_method_id",
                "source_payment_method_code",
                "source_payment_method_name",
                "source_active",
            )
        }
    if dataset_code == ErpDatasetCode.FUEL_SALES_ITEMS:
        return {
            k: normalized.get(k)
            for k in (
                "source_sale_id",
                "source_sale_item_id",
                "source_product_id",
                "source_quantity",
                "source_net_amount",
                "source_cancelled",
                "source_operation_type",
                "source_gross_amount",
                "source_discount_amount",
                "source_surcharge_amount",
                "source_cost_per_unit",
                "source_total_cost",
                "source_payment_method_id",
            )
        }
    if dataset_code == ErpDatasetCode.FUEL_RETAIL_PRICES:
        return {
            k: normalized.get(k)
            for k in (
                "source_branch_id",
                "source_product_id",
                "source_payment_method_id",
                "source_price_per_liter",
                "source_active",
                "source_effective_from",
            )
        }
    return normalized


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "sim"}:
        return True
    if text in {"0", "false", "f", "no", "n", "nao", "não"}:
        return False
    return default


def parse_source_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
