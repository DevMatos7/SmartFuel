"""Models Sprint 13 — ingestão inteligente de cotações por IA."""

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class QuoteIngestionBatch(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_ingestion_batches"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    source_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED", index=True)
    total_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteIngestionDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quote_ingestion_documents"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "sha256",
            name="uq_quote_ingestion_document_org_sha256",
        ),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_batches.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    source_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN_DOCUMENT")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UPLOADED", index=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_extraction_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    text_extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    source_message_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_sender: Mapped[str | None] = mapped_column(String(200), nullable=True)
    processing_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    processing_error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class QuoteAiExtraction(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_ai_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_documents.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="COMPLETED")
    structured_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    document_confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unparsed_fragments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteExtractionField(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_extraction_fields"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ai_extractions.id"), nullable=False, index=True
    )
    field_path: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    value_origin: Mapped[str] = mapped_column(String(40), nullable=False, default="EXTRACTED")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_region: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    validation_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteIngestionEntityMatch(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_ingestion_entity_matches"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_documents.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(255), nullable=False)
    matched_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    match_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_FOUND")
    candidate_entities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteIngestionReview(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_ingestion_reviews"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_documents.id"), nullable=False, index=True
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ai_extractions.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    corrections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteIngestionDraftLink(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_ingestion_draft_links"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_documents.id"), nullable=False, index=True
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_ingestion_reviews.id"), nullable=False, index=True
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False, index=True
    )
    creation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteAiProviderConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quote_ai_provider_configs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="mock")
    model: Mapped[str] = mapped_column(String(80), nullable=False, default="mock-extractor-v1")
    secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    temperature: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    maximum_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4000)
    daily_cost_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    monthly_cost_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    per_document_cost_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    allow_training_usage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class QuoteExtractionEvaluationCase(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_extraction_evaluation_cases"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteExtractionEvaluationRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_extraction_evaluation_runs"

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="RUNNING")
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
