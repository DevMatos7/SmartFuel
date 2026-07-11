import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class XpertSourceCreate(BaseModel):
    code: str = Field(max_length=60)
    name: str = Field(max_length=150)
    host: str = Field(max_length=255)
    port: int = Field(default=1433, ge=1, le=65535)
    database_name: str = Field(max_length=150)
    driver_name: str = Field(default="ODBC Driver 18 for SQL Server", max_length=150)
    encrypt_connection: bool = True
    trust_server_certificate: bool = False
    secret_ref: str = Field(max_length=150)
    source_timezone: str = Field(default="America/Cuiaba", max_length=80)
    enabled: bool = False


class XpertSourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database_name: str | None = Field(default=None, max_length=150)
    driver_name: str | None = Field(default=None, max_length=150)
    encrypt_connection: bool | None = None
    trust_server_certificate: bool | None = None
    secret_ref: str | None = Field(default=None, max_length=150)
    source_timezone: str | None = Field(default=None, max_length=80)
    enabled: bool | None = None


class XpertSourceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    host: str
    port: int
    database_name: str
    driver_name: str
    encrypt_connection: bool
    trust_server_certificate: bool
    secret_ref: str
    source_timezone: str
    enabled: bool
    connection_status: str
    security_status: str = "UNKNOWN"
    last_tested_at: datetime | None
    last_test_result: dict[str, Any] | None
    last_success_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class XpertConnectionTestResponse(BaseModel):
    status: str
    latency_ms: int | None = None
    server_version: str | None = None
    database_name: str | None = None
    source_utc_time: str | None = None
    encryption: bool = True
    privileges: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class XpertDatasetResponse(BaseModel):
    id: uuid.UUID
    erp_source_id: uuid.UUID
    code: str
    name: str
    query_file: str
    query_hash: str | None
    sync_mode: str
    checkpoint_type: str
    overlap_seconds: int
    batch_size: int
    schedule_enabled: bool
    schedule_interval_minutes: int | None
    next_scheduled_at: datetime | None
    contract_status: str
    contract_result: dict[str, Any] | None
    last_contract_validation_at: datetime | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class XpertDatasetUpdate(BaseModel):
    sync_mode: str | None = None
    overlap_seconds: int | None = Field(default=None, ge=0)
    batch_size: int | None = Field(default=None, gt=0)
    schedule_enabled: bool | None = None
    schedule_interval_minutes: int | None = Field(default=None, gt=0)
    enabled: bool | None = None


class XpertSyncRunCreate(BaseModel):
    source_id: uuid.UUID
    dataset_codes: list[str] = Field(min_length=1)
    station_ids: list[uuid.UUID] = Field(min_length=1)
    sync_mode: str = "FULL_SNAPSHOT_HASH"
    unsafe_homologation_acknowledged: bool = False
    history_start_date: date | None = None
    history_end_date: date | None = None


class XpertSyncRunResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    erp_source_id: uuid.UUID
    erp_dataset_id: uuid.UUID
    station_id: uuid.UUID | None
    trigger_type: str
    sync_mode: str
    status: str
    normalization_version: str | None = None
    hash_schema_version: int | None = None
    checkpoint_before: str | None
    checkpoint_after: str | None
    rows_read: int
    rows_staged: int
    rows_valid: int
    rows_applied: int
    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    rows_quarantined: int
    rows_error: int
    rows_marked_inactive: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class XpertSyncRunListResponse(BaseModel):
    items: list[XpertSyncRunResponse]
    total: int
    page: int
    page_size: int


class XpertSyncRunCreateResponse(BaseModel):
    runs: list[XpertSyncRunResponse]


class XpertCheckpointResponse(BaseModel):
    id: uuid.UUID
    erp_source_id: uuid.UUID
    erp_dataset_id: uuid.UUID
    station_id: uuid.UUID | None
    checkpoint_type: str
    watermark_value: str | None
    source_upper_bound: str | None
    last_success_at: datetime | None

    model_config = {"from_attributes": True}


class XpertCheckpointReset(BaseModel):
    mode: str = Field(pattern="^(CLEAR|SET)$")
    new_value: str | None = None
    reason: str = Field(min_length=5, max_length=500)


class XpertIntegrationSummary(BaseModel):
    status: str
    security_status: str | None = None
    source_id: str | None = None
    sources_count: int
    datasets_enabled: int
    pending_products: int
    pending_suppliers: int
    error_runs: int
    last_success_at: str | None
    odbc_available: bool = False
    worker_healthy: bool = False
    worker_last_heartbeat_at: str | None = None


class XpertSyncErrorResponse(BaseModel):
    id: uuid.UUID
    phase: str
    error_code: str
    message: str
    field_name: str | None
    source_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class XpertWorkerStatusResponse(BaseModel):
    worker_id: str | None = None
    last_heartbeat_at: datetime | None = None
    odbc_available: bool = False
    driver_name: str | None = None
    healthy: bool = False
    last_error: str | None = None


class XpertSupplierDocumentDiagnosticsResponse(BaseModel):
    run_id: uuid.UUID
    total_staged: int
    applied: int
    quarantined_invalid_document: int
    by_reason: dict[str, int]


class XpertStagingRecordResponse(BaseModel):
    id: uuid.UUID
    source_key: str
    processing_status: str
    record_hash: str | None
    source_updated_at: datetime | None
    applied_entity_type: str | None
    applied_entity_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
