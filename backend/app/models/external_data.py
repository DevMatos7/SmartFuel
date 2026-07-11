"""Models Sprint 9 — índices externos e séries de mercado."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ExternalDataSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "external_data_sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_external_data_sources_org_code"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="MISCONFIGURED", index=True)

    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)

    requires_credentials: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_scheduling: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    terms_review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    connector_status: Mapped[str] = mapped_column(String(40), nullable=False, default="MISCONFIGURED")
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    series: Mapped[list[ExternalSeries]] = relationship(back_populates="source")


class ExternalSeries(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "external_series"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_external_series_org_code"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_data_sources.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    source_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    calendar_type: Mapped[str] = mapped_column(String(40), nullable=False, default="CALENDAR_DAYS")
    freshness_grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    expected_publish_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    conversion_policy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outlier_pct_threshold: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    source: Mapped[ExternalDataSource] = relationship(back_populates="series")


class ExternalIngestionRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "external_ingestion_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_data_sources.id"), nullable=False, index=True
    )
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_series.id"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    records_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_revised: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    error_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalObservation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "external_observations"
    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "observation_datetime",
            "revision_number",
            name="uq_external_observations_series_obs_rev",
        ),
    )

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_series.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    observation_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reference_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    canonical_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    source_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT", index=True)

    external_identifier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_ingestion_runs.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalImportFile(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "external_import_files"

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_ingestion_runs.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_series.id"), nullable=True
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preview_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parse_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalQualityIssue(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "external_quality_issues"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_data_sources.id"), nullable=False, index=True
    )
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_series.id"), nullable=True, index=True
    )
    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_observations.id"), nullable=True, index=True
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_ingestion_runs.id"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    issue_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    resolution_status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)

    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
