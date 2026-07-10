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
