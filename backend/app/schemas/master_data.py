import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- Shared ---


class DeactivateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


# --- Products ---


class ProductCreate(BaseModel):
    code: str = Field(max_length=60)
    name: str = Field(max_length=150)
    fuel_family: str = Field(max_length=40)
    commercial_variant: str = Field(max_length=40)
    unit: str = Field(default="LITER", max_length=20)
    regulatory_code: str | None = Field(default=None, max_length=50)
    purchasable: bool = True
    sellable: bool = True
    display_order: int = 0
    active: bool = True


class ProductUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, max_length=150)
    fuel_family: str | None = Field(default=None, max_length=40)
    commercial_variant: str | None = Field(default=None, max_length=40)
    unit: str | None = Field(default=None, max_length=20)
    regulatory_code: str | None = Field(default=None, max_length=50)
    purchasable: bool | None = None
    sellable: bool | None = None
    display_order: int | None = None
    active: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    fuel_family: str
    commercial_variant: str
    unit: str
    regulatory_code: str | None
    purchasable: bool
    sellable: bool
    display_order: int
    active: bool
    code_locked: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


# --- ERP Products ---


class ErpProductResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID
    erp_product_id: str
    erp_product_code: str | None
    erp_description: str
    erp_unit: str | None
    erp_group_id: str | None
    erp_group_name: str | None
    erp_subgroup_id: str | None
    erp_subgroup_name: str | None
    canonical_product_id: uuid.UUID | None
    mapping_status: str
    mapping_source: str
    ignore_reason: str | None
    mapped_by: uuid.UUID | None
    mapped_at: datetime | None
    last_synced_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ErpProductListResponse(BaseModel):
    items: list[ErpProductResponse]
    total: int
    page: int
    page_size: int


class ErpProductMapRequest(BaseModel):
    canonical_product_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


class ErpProductBulkMapRequest(BaseModel):
    erp_product_ids: list[uuid.UUID] = Field(min_length=1)
    canonical_product_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


class ErpProductBulkMapFailure(BaseModel):
    erp_product_id: str
    code: str
    message: str


class ErpProductBulkMapResponse(BaseModel):
    mapped: list[ErpProductResponse]
    failures: list[ErpProductBulkMapFailure]


class ErpProductIgnoreRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ProductMappingHistoryResponse(BaseModel):
    id: uuid.UUID
    erp_product_id: uuid.UUID
    previous_product_id: uuid.UUID | None
    new_product_id: uuid.UUID | None
    previous_status: str | None
    new_status: str
    reason: str | None
    changed_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductMappingHistoryListResponse(BaseModel):
    items: list[ProductMappingHistoryResponse]


# --- Distributors ---


class DistributorCreate(BaseModel):
    internal_code: str = Field(max_length=60)
    corporate_name: str = Field(max_length=200)
    trade_name: str = Field(max_length=200)
    cnpj: str | None = Field(default=None, max_length=14)
    notes: str | None = None
    active: bool = True
    confirm_duplicate: bool = False


class DistributorUpdate(BaseModel):
    internal_code: str | None = Field(default=None, max_length=60)
    corporate_name: str | None = Field(default=None, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    cnpj: str | None = Field(default=None, max_length=14)
    notes: str | None = None
    active: bool | None = None
    confirm_duplicate: bool = False


class DistributorResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    internal_code: str
    corporate_name: str
    trade_name: str
    cnpj: str | None
    normalized_name: str
    registration_status: str
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DistributorListResponse(BaseModel):
    items: list[DistributorResponse]
    total: int
    page: int
    page_size: int


# --- Distribution Bases ---


class DistributionBaseCreate(BaseModel):
    distributor_id: uuid.UUID
    name: str = Field(max_length=150)
    city: str = Field(max_length=150)
    state: str = Field(min_length=2, max_length=2)
    external_code: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    active: bool = True


class DistributionBaseUpdate(BaseModel):
    distributor_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=150)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    external_code: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    active: bool | None = None


class DistributionBaseResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    distributor_id: uuid.UUID
    external_code: str | None
    name: str
    normalized_name: str
    city: str
    state: str
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DistributionBaseListResponse(BaseModel):
    items: list[DistributionBaseResponse]
    total: int
    page: int
    page_size: int


# --- ERP Suppliers ---


class ErpSupplierResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID
    erp_entity_id: str
    erp_entity_code: str | None
    erp_name: str
    erp_cnpj: str | None
    distributor_id: uuid.UUID | None
    mapping_status: str
    ignore_reason: str | None
    mapped_by: uuid.UUID | None
    mapped_at: datetime | None
    last_synced_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ErpSupplierListResponse(BaseModel):
    items: list[ErpSupplierResponse]
    total: int
    page: int
    page_size: int


class ErpSupplierMapRequest(BaseModel):
    distributor_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


class ErpSupplierIgnoreRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


# --- Payment Terms ---


class PaymentTermCreate(BaseModel):
    code: str = Field(max_length=60)
    name: str = Field(max_length=120)
    payment_type: str = Field(max_length=30)
    days: int
    description: str | None = None
    active: bool = True


class PaymentTermUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, max_length=120)
    payment_type: str | None = Field(default=None, max_length=30)
    days: int | None = None
    description: str | None = None
    active: bool | None = None


class PaymentTermResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    normalized_name: str
    payment_type: str
    days: int
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentTermListResponse(BaseModel):
    items: list[PaymentTermResponse]
    total: int
    page: int
    page_size: int


# --- Supplier Rules ---


class SupplierRuleCreate(BaseModel):
    station_id: uuid.UUID
    distributor_id: uuid.UUID
    product_id: uuid.UUID | None = None
    distribution_base_id: uuid.UUID | None = None
    allowed: bool = True
    minimum_volume_liters: Decimal = Field(default=Decimal("5000.000"), gt=0)
    valid_from: date
    valid_until: date | None = None
    contract_reference: str | None = Field(default=None, max_length=150)
    reason: str | None = None
    notes: str | None = None
    priority: int = 100
    active: bool = True


class SupplierRuleUpdate(BaseModel):
    station_id: uuid.UUID | None = None
    distributor_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    distribution_base_id: uuid.UUID | None = None
    allowed: bool | None = None
    minimum_volume_liters: Decimal | None = Field(default=None, gt=0)
    valid_from: date | None = None
    valid_until: date | None = None
    contract_reference: str | None = Field(default=None, max_length=150)
    reason: str | None = None
    notes: str | None = None
    priority: int | None = None
    active: bool | None = None


class SupplierRuleResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID
    distributor_id: uuid.UUID
    product_id: uuid.UUID | None
    distribution_base_id: uuid.UUID | None
    allowed: bool
    minimum_volume_liters: Decimal
    valid_from: date
    valid_until: date | None
    contract_reference: str | None
    reason: str | None
    notes: str | None
    priority: int
    active: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierRuleListResponse(BaseModel):
    items: list[SupplierRuleResponse]
    total: int
    page: int
    page_size: int


class CloseValidityRequest(BaseModel):
    valid_until: date
    reason: str | None = Field(default=None, max_length=500)


class EffectiveRuleResponse(BaseModel):
    allowed: bool
    minimum_volume_liters: Decimal
    rule_source: str
    rule_id: uuid.UUID | None
    distribution_base_id: uuid.UUID | None = None
    valid_from: date | None
    valid_until: date | None
    reason: str | None


# --- Master Data Imports ---


class MasterDataImportRowResponse(BaseModel):
    id: uuid.UUID
    import_job_id: uuid.UUID
    row_number: int
    external_identifier: str | None
    action: str
    status: str
    raw_data: dict
    normalized_data: dict | None
    validation_errors: dict | None
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class MasterDataImportJobResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID | None
    import_type: str
    source_file_name: str
    source_file_hash: str
    status: str
    records_total: int
    records_valid: int
    records_inserted: int
    records_updated: int
    records_unchanged: int
    records_failed: int
    error_summary: dict | None
    created_by: uuid.UUID
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class MasterDataImportJobDetailResponse(MasterDataImportJobResponse):
    rows: list[MasterDataImportRowResponse]


class MasterDataImportJobListResponse(BaseModel):
    items: list[MasterDataImportJobResponse]
    total: int
    page: int
    page_size: int
