from __future__ import annotations

from dataclasses import dataclass, field

from app.core.xpert_sync_enums import ErpDatasetCode


@dataclass(frozen=True)
class DatasetColumnContract:
    name: str
    required: bool = False


@dataclass(frozen=True)
class DatasetContract:
    code: str
    columns: tuple[DatasetColumnContract, ...]

    def required_columns(self) -> set[str]:
        return {col.name for col in self.columns if col.required}

    def all_columns(self) -> set[str]:
        return {col.name for col in self.columns}


DATASET_CONTRACTS: dict[str, DatasetContract] = {
    ErpDatasetCode.PRODUCTS: DatasetContract(
        code=ErpDatasetCode.PRODUCTS,
        columns=(
            DatasetColumnContract("source_product_id", required=True),
            DatasetColumnContract("source_product_code"),
            DatasetColumnContract("source_description", required=True),
            DatasetColumnContract("source_unit"),
            DatasetColumnContract("source_group_id"),
            DatasetColumnContract("source_group_name"),
            DatasetColumnContract("source_subgroup_id"),
            DatasetColumnContract("source_subgroup_name"),
            DatasetColumnContract("source_updated_at"),
            DatasetColumnContract("source_active"),
        ),
    ),
    ErpDatasetCode.SUPPLIERS: DatasetContract(
        code=ErpDatasetCode.SUPPLIERS,
        columns=(
            DatasetColumnContract("source_supplier_id", required=True),
            DatasetColumnContract("source_supplier_code"),
            DatasetColumnContract("source_name", required=True),
            DatasetColumnContract("source_cnpj"),
            DatasetColumnContract("source_updated_at"),
            DatasetColumnContract("source_active"),
        ),
    ),
    ErpDatasetCode.STATIONS: DatasetContract(
        code=ErpDatasetCode.STATIONS,
        columns=(
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_trade_name"),
            DatasetColumnContract("source_cnpj"),
            DatasetColumnContract("source_active"),
        ),
    ),
    ErpDatasetCode.PAYMENT_METHODS: DatasetContract(
        code=ErpDatasetCode.PAYMENT_METHODS,
        columns=(
            DatasetColumnContract("source_payment_method_id", required=True),
            DatasetColumnContract("source_payment_method_code"),
            DatasetColumnContract("source_payment_method_name", required=True),
            DatasetColumnContract("source_active"),
            DatasetColumnContract("source_updated_at"),
        ),
    ),
    ErpDatasetCode.FUEL_SALES_ITEMS: DatasetContract(
        code=ErpDatasetCode.FUEL_SALES_ITEMS,
        columns=(
            DatasetColumnContract("source_sale_id", required=True),
            DatasetColumnContract("source_sale_item_id", required=True),
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_sale_datetime", required=True),
            DatasetColumnContract("source_business_date", required=True),
            DatasetColumnContract("source_product_id", required=True),
            DatasetColumnContract("source_quantity", required=True),
            DatasetColumnContract("source_net_amount", required=True),
            DatasetColumnContract("source_updated_at", required=True),
            DatasetColumnContract("source_cancelled", required=True),
            DatasetColumnContract("source_document_number"),
            DatasetColumnContract("source_unit"),
            DatasetColumnContract("source_unit_price"),
            DatasetColumnContract("source_gross_amount"),
            DatasetColumnContract("source_discount_amount"),
            DatasetColumnContract("source_surcharge_amount"),
            DatasetColumnContract("source_cost_per_unit"),
            DatasetColumnContract("source_total_cost"),
            DatasetColumnContract("source_cfop"),
            DatasetColumnContract("source_payment_method_id"),
            DatasetColumnContract("source_operation_type"),
        ),
    ),
    ErpDatasetCode.FUEL_RETAIL_PRICES: DatasetContract(
        code=ErpDatasetCode.FUEL_RETAIL_PRICES,
        columns=(
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_product_id", required=True),
            DatasetColumnContract("source_payment_method_id", required=True),
            DatasetColumnContract("source_price_per_liter", required=True),
            DatasetColumnContract("source_active", required=True),
            DatasetColumnContract("source_effective_from"),
            DatasetColumnContract("source_effective_until"),
            DatasetColumnContract("source_updated_at"),
        ),
    ),
    ErpDatasetCode.FUEL_PURCHASE_INVOICES: DatasetContract(
        code=ErpDatasetCode.FUEL_PURCHASE_INVOICES,
        columns=(
            DatasetColumnContract("source_invoice_id", required=True),
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_supplier_id", required=True),
            DatasetColumnContract("source_document_number", required=True),
            DatasetColumnContract("source_issue_date", required=True),
            DatasetColumnContract("source_entry_date", required=True),
            DatasetColumnContract("source_total_amount", required=True),
            DatasetColumnContract("source_status", required=True),
            DatasetColumnContract("source_updated_at", required=True),
            DatasetColumnContract("source_series"),
            DatasetColumnContract("source_access_key"),
            DatasetColumnContract("source_operation_type"),
            DatasetColumnContract("source_freight_amount"),
            DatasetColumnContract("source_discount_amount"),
            DatasetColumnContract("source_insurance_amount"),
            DatasetColumnContract("source_other_expenses"),
            DatasetColumnContract("source_tax_amount"),
            DatasetColumnContract("source_xml_imported_in_erp"),
            DatasetColumnContract("source_cancelled"),
            DatasetColumnContract("source_base_id"),
            DatasetColumnContract("source_payment_condition_id"),
        ),
    ),
    ErpDatasetCode.FUEL_PURCHASE_ITEMS: DatasetContract(
        code=ErpDatasetCode.FUEL_PURCHASE_ITEMS,
        columns=(
            DatasetColumnContract("source_invoice_id", required=True),
            DatasetColumnContract("source_invoice_item_id", required=True),
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_supplier_id", required=True),
            DatasetColumnContract("source_product_id", required=True),
            DatasetColumnContract("source_quantity", required=True),
            DatasetColumnContract("source_unit", required=True),
            DatasetColumnContract("source_unit_price", required=True),
            DatasetColumnContract("source_item_total", required=True),
            DatasetColumnContract("source_updated_at", required=True),
            DatasetColumnContract("source_product_description"),
            DatasetColumnContract("source_cfop"),
            DatasetColumnContract("source_ncm"),
            DatasetColumnContract("source_discount_amount"),
            DatasetColumnContract("source_freight_amount"),
            DatasetColumnContract("source_insurance_amount"),
            DatasetColumnContract("source_other_expenses"),
            DatasetColumnContract("source_icms_amount"),
            DatasetColumnContract("source_icms_st_amount"),
            DatasetColumnContract("source_fcp_amount"),
            DatasetColumnContract("source_pis_amount"),
            DatasetColumnContract("source_cofins_amount"),
            DatasetColumnContract("source_total_cost"),
            DatasetColumnContract("source_cost_per_unit"),
            DatasetColumnContract("source_cancelled"),
            DatasetColumnContract("source_operation_type"),
        ),
    ),
    ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES: DatasetContract(
        code=ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
        columns=(
            DatasetColumnContract("source_title_id", required=True),
            DatasetColumnContract("source_branch_id", required=True),
            DatasetColumnContract("source_supplier_id", required=True),
            DatasetColumnContract("source_invoice_id", required=True),
            DatasetColumnContract("source_due_date", required=True),
            DatasetColumnContract("source_original_amount", required=True),
            DatasetColumnContract("source_open_amount", required=True),
            DatasetColumnContract("source_status", required=True),
            DatasetColumnContract("source_updated_at", required=True),
            DatasetColumnContract("source_installment_number"),
            DatasetColumnContract("source_document_number"),
            DatasetColumnContract("source_issue_date"),
            DatasetColumnContract("source_payment_date"),
            DatasetColumnContract("source_paid_amount"),
            DatasetColumnContract("source_interest_amount"),
            DatasetColumnContract("source_penalty_amount"),
            DatasetColumnContract("source_discount_amount"),
            DatasetColumnContract("source_bank_or_wallet"),
            DatasetColumnContract("source_payment_method"),
            DatasetColumnContract("source_cancelled"),
        ),
    ),
}


@dataclass
class ContractValidationResult:
    valid: bool
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    found_columns: list[str] = field(default_factory=list)


def validate_contract(dataset_code: str, columns: list[str]) -> ContractValidationResult:
    contract = DATASET_CONTRACTS.get(dataset_code)
    if contract is None:
        return ContractValidationResult(valid=False, missing_columns=[dataset_code])
    found = {col.lower() for col in columns}
    expected = {col.lower() for col in contract.all_columns()}
    required = {col.lower() for col in contract.required_columns()}
    missing = sorted(required - found)
    extra = sorted(found - expected)
    return ContractValidationResult(
        valid=not missing,
        missing_columns=missing,
        extra_columns=extra,
        found_columns=sorted(found),
    )
