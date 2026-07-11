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
            "source_cfop": _clean_str(lowered.get("source_cfop")),
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
            "valor_formapgto_mapping_source": "LEGACY_REFERENCE",
            "valor_formapgto_mapping_status": "PROVISIONAL",
        }

    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
        return {
            "source_invoice_id": _clean_str(lowered.get("source_invoice_id")),
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_supplier_id": _clean_str(lowered.get("source_supplier_id")),
            "source_document_number": _clean_str(lowered.get("source_document_number")),
            "source_issue_date": lowered.get("source_issue_date"),
            "source_entry_date": lowered.get("source_entry_date"),
            "source_total_amount": lowered.get("source_total_amount"),
            "source_status": _clean_str(lowered.get("source_status")),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
            "source_series": _clean_str(lowered.get("source_series")),
            "source_access_key": _clean_str(lowered.get("source_access_key")),
            "source_operation_type": _clean_str(lowered.get("source_operation_type")) or "PURCHASE",
            "source_freight_amount": lowered.get("source_freight_amount"),
            "source_discount_amount": lowered.get("source_discount_amount"),
            "source_insurance_amount": lowered.get("source_insurance_amount"),
            "source_other_expenses": lowered.get("source_other_expenses"),
            "source_tax_amount": lowered.get("source_tax_amount"),
            "source_xml_imported_in_erp": _to_bool(
                lowered.get("source_xml_imported_in_erp", lowered.get("source_xml_available")),
                default=False,
            ),
            "source_cancelled": _to_bool(lowered.get("source_cancelled"), default=False),
            "source_base_id": _clean_str(lowered.get("source_base_id")),
            "source_payment_condition_id": _clean_str(lowered.get("source_payment_condition_id")),
        }

    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS:
        return {
            "source_invoice_id": _clean_str(lowered.get("source_invoice_id")),
            "source_invoice_item_id": _clean_str(lowered.get("source_invoice_item_id")),
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_supplier_id": _clean_str(lowered.get("source_supplier_id")),
            "source_product_id": _clean_str(lowered.get("source_product_id")),
            "source_quantity": lowered.get("source_quantity"),
            "source_unit": _clean_str(lowered.get("source_unit")),
            "source_unit_price": lowered.get("source_unit_price"),
            "source_item_total": lowered.get("source_item_total"),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
            "source_product_description": _clean_str(lowered.get("source_product_description")),
            "source_cfop": _clean_str(lowered.get("source_cfop")),
            "source_ncm": _clean_str(lowered.get("source_ncm")),
            "source_discount_amount": lowered.get("source_discount_amount"),
            "source_freight_amount": lowered.get("source_freight_amount"),
            "source_insurance_amount": lowered.get("source_insurance_amount"),
            "source_other_expenses": lowered.get("source_other_expenses"),
            "source_icms_amount": lowered.get("source_icms_amount"),
            "source_icms_st_amount": lowered.get("source_icms_st_amount"),
            "source_fcp_amount": lowered.get("source_fcp_amount"),
            "source_pis_amount": lowered.get("source_pis_amount"),
            "source_cofins_amount": lowered.get("source_cofins_amount"),
            "source_total_cost": lowered.get("source_total_cost"),
            "source_cost_per_unit": lowered.get("source_cost_per_unit"),
            "source_cancelled": _to_bool(lowered.get("source_cancelled"), default=False),
            "source_operation_type": _clean_str(lowered.get("source_operation_type")) or "PURCHASE",
        }

    if dataset_code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
        return {
            "source_title_id": _clean_str(lowered.get("source_title_id")),
            "source_branch_id": _clean_str(lowered.get("source_branch_id")),
            "source_supplier_id": _clean_str(lowered.get("source_supplier_id")),
            "source_invoice_id": _clean_str(lowered.get("source_invoice_id")),
            "source_due_date": lowered.get("source_due_date"),
            "source_original_amount": lowered.get("source_original_amount"),
            "source_open_amount": lowered.get("source_open_amount"),
            "source_status": _clean_str(lowered.get("source_status")),
            "source_updated_at": parse_source_datetime(lowered.get("source_updated_at")),
            "source_installment_number": lowered.get("source_installment_number"),
            "source_document_number": _clean_str(lowered.get("source_document_number")),
            "source_issue_date": lowered.get("source_issue_date"),
            "source_payment_date": lowered.get("source_payment_date"),
            "source_paid_amount": lowered.get("source_paid_amount"),
            "source_interest_amount": lowered.get("source_interest_amount"),
            "source_penalty_amount": lowered.get("source_penalty_amount"),
            "source_discount_amount": lowered.get("source_discount_amount"),
            "source_bank_or_wallet": _clean_str(lowered.get("source_bank_or_wallet")),
            "source_payment_method": _clean_str(lowered.get("source_payment_method")),
            "source_cancelled": _to_bool(lowered.get("source_cancelled"), default=False),
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
    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
        return normalized["source_invoice_id"]
    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS:
        return f"{normalized['source_invoice_id']}:{normalized['source_invoice_item_id']}"
    if dataset_code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
        return normalized["source_title_id"]
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
                "source_cfop",
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
    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
        return {
            "normalization_version": "FUEL_PURCHASE_V1",
            "hash_schema_version": 1,
            **{
                k: normalized.get(k)
                for k in (
                    "source_invoice_id",
                    "source_supplier_id",
                    "source_document_number",
                    "source_issue_date",
                    "source_entry_date",
                    "source_total_amount",
                    "source_status",
                    "source_series",
                    "source_access_key",
                    "source_operation_type",
                    "source_freight_amount",
                    "source_discount_amount",
                    "source_insurance_amount",
                    "source_other_expenses",
                    "source_tax_amount",
                    "source_xml_imported_in_erp",
                    "source_cancelled",
                )
            },
        }
    if dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS:
        return {
            "normalization_version": "FUEL_PURCHASE_V1",
            "hash_schema_version": 1,
            **{
                k: normalized.get(k)
                for k in (
                    "source_invoice_id",
                    "source_invoice_item_id",
                    "source_product_id",
                    "source_quantity",
                    "source_unit",
                    "source_unit_price",
                    "source_item_total",
                    "source_discount_amount",
                    "source_freight_amount",
                    "source_insurance_amount",
                    "source_other_expenses",
                    "source_total_cost",
                    "source_cost_per_unit",
                    "source_cancelled",
                    "source_operation_type",
                    "source_cfop",
                )
            },
        }
    if dataset_code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
        return {
            "normalization_version": "FUEL_PURCHASE_V1",
            "hash_schema_version": 1,
            **{
                k: normalized.get(k)
                for k in (
                    "source_title_id",
                    "source_invoice_id",
                    "source_supplier_id",
                    "source_due_date",
                    "source_original_amount",
                    "source_open_amount",
                    "source_paid_amount",
                    "source_status",
                    "source_cancelled",
                    "source_payment_date",
                    "source_interest_amount",
                    "source_penalty_amount",
                    "source_discount_amount",
                )
            },
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
