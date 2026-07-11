from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ErpSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_sources"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_erp_sources_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False, default="XPERT_SQLSERVER")
    connector_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="DIRECT")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=1433)
    database_name: Mapped[str] = mapped_column(String(150), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(150), nullable=False)
    encrypt_connection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trust_server_certificate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    secret_ref: Mapped[str] = mapped_column(String(150), nullable=False)
    source_timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="America/Cuiaba")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    connection_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    security_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    datasets: Mapped[list["ErpDataset"]] = relationship("ErpDataset", back_populates="source")


class ErpDataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_datasets"
    __table_args__ = (UniqueConstraint("erp_source_id", "code", name="uq_erp_datasets_source_code"),)

    erp_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    query_file: Mapped[str] = mapped_column(String(255), nullable=False)
    query_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="FULL_SNAPSHOT_HASH")
    checkpoint_type: Mapped[str] = mapped_column(String(40), nullable=False, default="NONE")
    source_timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    overlap_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    strict_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_partial_checkpoint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    contract_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_contract_validation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source: Mapped["ErpSource"] = relationship("ErpSource", back_populates="datasets")


class ErpSyncCheckpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_sync_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "erp_source_id",
            "erp_dataset_id",
            "station_id",
            name="uq_erp_sync_checkpoints_source_dataset_station",
        ),
    )

    erp_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    erp_dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    checkpoint_type: Mapped[str] = mapped_column(String(40), nullable=False, default="NONE")
    watermark_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_upper_bound: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_success_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ErpSyncRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "erp_sync_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    erp_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    erp_dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sync_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="QUEUED", index=True)
    checkpoint_before: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkpoint_after: Mapped[str | None] = mapped_column(String(255), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_upper_bound: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    query_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalization_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hash_schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    rows_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_staged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_applied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_quarantined: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_marked_inactive: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_batch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_batches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retried_from_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    staging_records: Mapped[list["ErpStagingRecord"]] = relationship(
        "ErpStagingRecord", back_populates="run", cascade="all, delete-orphan"
    )
    errors: Mapped[list["ErpSyncError"]] = relationship(
        "ErpSyncError", back_populates="run", cascade="all, delete-orphan"
    )


class ErpStagingRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "erp_staging_records"
    __table_args__ = (
        UniqueConstraint("sync_run_id", "source_key", name="uq_erp_staging_records_run_source_key"),
    )

    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True)
    dataset_code: Mapped[str] = mapped_column(String(60), nullable=False)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    processing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="RECEIVED", index=True)
    validation_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    applied_entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    applied_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["ErpSyncRun"] = relationship("ErpSyncRun", back_populates="staging_records")


class ErpSyncError(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "erp_sync_errors"

    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staging_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_staging_records.id", ondelete="SET NULL"), nullable=True
    )
    phase: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped["ErpSyncRun"] = relationship("ErpSyncRun", back_populates="errors")


class XpertWorkerStatus(Base):
    __tablename__ = "xpert_worker_status"

    worker_id: Mapped[str] = mapped_column(String(150), primary_key=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    odbc_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    driver_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
