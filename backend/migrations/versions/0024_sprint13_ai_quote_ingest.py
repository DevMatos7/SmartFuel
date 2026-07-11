"""Sprint 13 — ingestão inteligente de cotações por IA."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_sprint13_ai_quote_ingest"
down_revision: str | None = "0023_sprint12_ops_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quote_ingestion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("source_channel", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="CREATED"),
        sa.Column("total_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ready_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_ingest_batches_org", "quote_ingestion_batches", ["organization_id"])
    op.create_index("ix_quote_ingest_batches_station", "quote_ingestion_batches", ["station_id"])
    op.create_index("ix_quote_ingest_batches_status", "quote_ingestion_batches", ["status"])

    op.create_table(
        "quote_ingestion_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_batches.id"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("source_channel", sa.String(40), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False, server_default="UNKNOWN_DOCUMENT"),
        sa.Column("status", sa.String(40), nullable=False, server_default="UPLOADED"),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("text_extraction_method", sa.String(40), nullable=True),
        sa.Column("text_extraction_confidence", sa.Numeric(8, 6), nullable=True),
        sa.Column("source_message_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_sender", sa.String(200), nullable=True),
        sa.Column("processing_error_code", sa.String(80), nullable=True),
        sa.Column("processing_error_details", postgresql.JSONB(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id",
            "sha256",
            name="uq_quote_ingestion_document_org_sha256",
        ),
    )
    op.create_index("ix_quote_ingest_docs_batch", "quote_ingestion_documents", ["batch_id"])
    op.create_index("ix_quote_ingest_docs_org", "quote_ingestion_documents", ["organization_id"])
    op.create_index("ix_quote_ingest_docs_station", "quote_ingestion_documents", ["station_id"])
    op.create_index("ix_quote_ingest_docs_status", "quote_ingestion_documents", ["status"])
    op.create_index("ix_quote_ingest_docs_sha256", "quote_ingestion_documents", ["sha256"])

    op.create_table(
        "quote_ai_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_documents.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="COMPLETED"),
        sa.Column("structured_output", postgresql.JSONB(), nullable=True),
        sa.Column("raw_provider_response", postgresql.JSONB(), nullable=True),
        sa.Column("document_confidence", sa.Numeric(8, 6), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("unparsed_fragments", postgresql.JSONB(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("cost_currency", sa.String(10), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_ai_extractions_doc", "quote_ai_extractions", ["document_id"])
    op.create_index("ix_quote_ai_extractions_status", "quote_ai_extractions", ["status"])

    op.create_table(
        "quote_extraction_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "extraction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ai_extractions.id"),
            nullable=False,
        ),
        sa.Column("field_path", sa.String(200), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", postgresql.JSONB(), nullable=True),
        sa.Column("value_origin", sa.String(40), nullable=False, server_default="EXTRACTED"),
        sa.Column("confidence", sa.Numeric(8, 6), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("evidence_page", sa.Integer(), nullable=True),
        sa.Column("evidence_region", postgresql.JSONB(), nullable=True),
        sa.Column("validation_status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_extract_fields_extraction", "quote_extraction_fields", ["extraction_id"])

    op.create_table(
        "quote_ingestion_entity_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_documents.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("raw_value", sa.String(255), nullable=False),
        sa.Column("matched_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_method", sa.String(40), nullable=True),
        sa.Column("match_confidence", sa.Numeric(8, 6), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="NOT_FOUND"),
        sa.Column("candidate_entities", postgresql.JSONB(), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_entity_matches_doc", "quote_ingestion_entity_matches", ["document_id"])
    op.create_index("ix_quote_entity_matches_status", "quote_ingestion_entity_matches", ["status"])

    op.create_table(
        "quote_ingestion_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_documents.id"),
            nullable=False,
        ),
        sa.Column(
            "extraction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ai_extractions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("corrections", postgresql.JSONB(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_ingest_reviews_doc", "quote_ingestion_reviews", ["document_id"])
    op.create_index("ix_quote_ingest_reviews_extraction", "quote_ingestion_reviews", ["extraction_id"])
    op.create_index("ix_quote_ingest_reviews_status", "quote_ingestion_reviews", ["status"])

    op.create_table(
        "quote_ingestion_draft_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_documents.id"),
            nullable=False,
        ),
        sa.Column(
            "review_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_ingestion_reviews.id"),
            nullable=False,
        ),
        sa.Column(
            "quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id"),
            nullable=False,
        ),
        sa.Column("creation_status", sa.String(40), nullable=False, server_default="CREATED"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_draft_links_doc", "quote_ingestion_draft_links", ["document_id"])
    op.create_index("ix_quote_draft_links_review", "quote_ingestion_draft_links", ["review_id"])
    op.create_index("ix_quote_draft_links_quote", "quote_ingestion_draft_links", ["quote_id"])

    op.create_table(
        "quote_ai_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(40), nullable=False, server_default="mock"),
        sa.Column("model", sa.String(80), nullable=False, server_default="mock-extractor-v1"),
        sa.Column("secret_ref", sa.String(200), nullable=True),
        sa.Column("prompt_version", sa.String(40), nullable=False, server_default="v1"),
        sa.Column("schema_version", sa.String(40), nullable=False, server_default="v1"),
        sa.Column("temperature", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("maximum_tokens", sa.Integer(), nullable=False, server_default="4000"),
        sa.Column("daily_cost_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("monthly_cost_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("per_document_cost_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("allow_training_usage", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_ai_provider_configs_org", "quote_ai_provider_configs", ["organization_id"])

    op.create_table(
        "quote_extraction_evaluation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("document_storage_key", sa.String(500), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("expected_output", postgresql.JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_eval_cases_org", "quote_extraction_evaluation_cases", ["organization_id"])

    op.create_table(
        "quote_extraction_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="RUNNING"),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quote_eval_runs_status", "quote_extraction_evaluation_runs", ["status"])


def downgrade() -> None:
    op.drop_table("quote_extraction_evaluation_runs")
    op.drop_table("quote_extraction_evaluation_cases")
    op.drop_table("quote_ai_provider_configs")
    op.drop_table("quote_ingestion_draft_links")
    op.drop_table("quote_ingestion_reviews")
    op.drop_table("quote_ingestion_entity_matches")
    op.drop_table("quote_extraction_fields")
    op.drop_table("quote_ai_extractions")
    op.drop_table("quote_ingestion_documents")
    op.drop_table("quote_ingestion_batches")
