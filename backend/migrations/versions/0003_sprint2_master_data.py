"""Sprint 2 — produtos, distribuidoras, bases, condições e mapeamento ERP."""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_sprint2_master_data"
down_revision: str | None = "0002_sprint1_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCT_SEEDS = [
    ("ETANOL_HIDRATADO", "Etanol hidratado", "ETHANOL", "COMMON", 10),
    ("GASOLINA_C_COMUM", "Gasolina C comum", "GASOLINE_C", "COMMON", 20),
    ("GASOLINA_C_ADITIVADA", "Gasolina C aditivada", "GASOLINE_C", "ADDITIVATED", 30),
    ("DIESEL_B_S10_COMUM", "Diesel B S10 comum", "DIESEL_B_S10", "COMMON", 40),
    ("DIESEL_B_S10_ADITIVADO", "Diesel B S10 aditivado", "DIESEL_B_S10", "ADDITIVATED", 50),
    ("DIESEL_B_S500_COMUM", "Diesel B S500 comum", "DIESEL_B_S500", "COMMON", 60),
]

PAYMENT_TERM_SEEDS = [
    ("CASH_0", "À vista", "CASH", 0),
    ("TERM_7", "Prazo 7 dias", "TERM", 7),
    ("TERM_15", "Prazo 15 dias", "TERM", 15),
    ("TERM_21", "Prazo 21 dias", "TERM", 21),
    ("TERM_30", "Prazo 30 dias", "TERM", 30),
    ("ANTICIPATED_0", "Antecipado", "ANTICIPATED", 0),
]


def _seed_master_data(conn: sa.Connection) -> None:
    orgs = conn.execute(sa.text("SELECT id FROM organizations")).fetchall()
    for (org_id,) in orgs:
        for code, name, family, variant, order in PRODUCT_SEEDS:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO products (
                        id, organization_id, code, name, fuel_family, commercial_variant,
                        unit, purchasable, sellable, display_order, active, code_locked,
                        created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :org_id, :code, :name, :family, :variant,
                           'LITER', true, true, :display_order, true, false, now(), now()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM products WHERE organization_id = :org_id AND code = :code
                    )
                    """
                ),
                {
                    "org_id": org_id,
                    "code": code,
                    "name": name,
                    "family": family,
                    "variant": variant,
                    "display_order": order,
                },
            )
        for code, name, payment_type, days in PAYMENT_TERM_SEEDS:
            normalized = name.upper()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO payment_terms (
                        id, organization_id, code, name, normalized_name, payment_type, days,
                        active, created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :org_id, :code, :name, :normalized, :ptype, :days,
                           true, now(), now()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM payment_terms WHERE organization_id = :org_id AND code = :code
                    )
                    """
                ),
                {
                    "org_id": org_id,
                    "code": code,
                    "name": name,
                    "normalized": normalized,
                    "ptype": payment_type,
                    "days": days,
                },
            )


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("fuel_family", sa.String(length=40), nullable=False),
        sa.Column("commercial_variant", sa.String(length=40), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default="LITER"),
        sa.Column("regulatory_code", sa.String(length=50), nullable=True),
        sa.Column("purchasable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sellable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("code_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_products_org_code"),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])
    op.create_index("ix_products_code", "products", ["code"])

    op.create_table(
        "erp_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("erp_product_id", sa.String(length=100), nullable=False),
        sa.Column("erp_product_code", sa.String(length=100), nullable=True),
        sa.Column("erp_description", sa.String(length=255), nullable=False),
        sa.Column("erp_unit", sa.String(length=30), nullable=True),
        sa.Column("erp_group_id", sa.String(length=100), nullable=True),
        sa.Column("erp_group_name", sa.String(length=150), nullable=True),
        sa.Column("erp_subgroup_id", sa.String(length=100), nullable=True),
        sa.Column("erp_subgroup_name", sa.String(length=150), nullable=True),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("mapping_status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("mapping_source", sa.String(length=30), nullable=False, server_default="MANUAL"),
        sa.Column("ignore_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("mapped_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("station_id", "erp_product_id", name="uq_erp_products_station_erp_id"),
    )
    op.create_index("ix_erp_products_station_id", "erp_products", ["station_id"])
    op.create_index("ix_erp_products_erp_product_id", "erp_products", ["erp_product_id"])
    op.create_index("ix_erp_products_mapping_status", "erp_products", ["mapping_status"])
    op.create_index("ix_erp_products_canonical_product_id", "erp_products", ["canonical_product_id"])

    op.create_table(
        "product_mapping_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("erp_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("new_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_product_mapping_history_erp_product_id", "product_mapping_history", ["erp_product_id"])

    op.create_table(
        "distributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("internal_code", sa.String(length=60), nullable=False),
        sa.Column("corporate_name", sa.String(length=200), nullable=False),
        sa.Column("trade_name", sa.String(length=200), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("registration_status", sa.String(length=30), nullable=False, server_default="INCOMPLETE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_distributors_organization_id", "distributors", ["organization_id"])
    op.create_index("ix_distributors_cnpj", "distributors", ["cnpj"])
    op.create_index("ix_distributors_normalized_name", "distributors", ["normalized_name"])
    op.create_index(
        "uq_distributors_org_cnpj",
        "distributors",
        ["organization_id", "cnpj"],
        unique=True,
        postgresql_where=sa.text("cnpj IS NOT NULL"),
    )

    op.create_table(
        "erp_suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("erp_entity_id", sa.String(length=100), nullable=False),
        sa.Column("erp_entity_code", sa.String(length=100), nullable=True),
        sa.Column("erp_name", sa.String(length=255), nullable=False),
        sa.Column("erp_cnpj", sa.String(length=14), nullable=True),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("mapping_status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("ignore_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("mapped_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("station_id", "erp_entity_id", name="uq_erp_suppliers_station_entity"),
    )
    op.create_index("ix_erp_suppliers_station_id", "erp_suppliers", ["station_id"])
    op.create_index("ix_erp_suppliers_erp_entity_id", "erp_suppliers", ["erp_entity_id"])
    op.create_index("ix_erp_suppliers_mapping_status", "erp_suppliers", ["mapping_status"])

    op.create_table(
        "distribution_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=False),
        sa.Column("external_code", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("normalized_name", sa.String(length=150), nullable=False),
        sa.Column("city", sa.String(length=150), nullable=False),
        sa.Column("state", sa.CHAR(length=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "distributor_id", "state", "normalized_name",
            name="uq_distribution_bases_distributor_state_name",
        ),
    )
    op.create_index("ix_distribution_bases_distributor_id", "distribution_bases", ["distributor_id"])
    op.create_index("ix_distribution_bases_normalized_name", "distribution_bases", ["normalized_name"])

    op.create_table(
        "payment_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_payment_terms_org_code"),
        sa.UniqueConstraint(
            "organization_id", "payment_type", "days", "normalized_name",
            name="uq_payment_terms_org_type_days_name",
        ),
    )
    op.create_index("ix_payment_terms_organization_id", "payment_terms", ["organization_id"])
    op.create_index("ix_payment_terms_payment_type", "payment_terms", ["payment_type"])

    op.create_table(
        "station_supplier_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("distribution_base_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distribution_bases.id"), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("minimum_volume_liters", sa.Numeric(16, 3), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("contract_reference", sa.String(length=150), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("minimum_volume_liters > 0", name="ck_station_supplier_rules_min_volume"),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_station_supplier_rules_validity",
        ),
    )
    op.create_index("ix_station_supplier_rules_station_id", "station_supplier_rules", ["station_id"])
    op.create_index("ix_station_supplier_rules_distributor_id", "station_supplier_rules", ["distributor_id"])
    op.create_index("ix_station_supplier_rules_product_id", "station_supplier_rules", ["product_id"])
    op.create_index("ix_station_supplier_rules_valid_from", "station_supplier_rules", ["valid_from"])
    op.create_index("ix_station_supplier_rules_valid_until", "station_supplier_rules", ["valid_until"])

    op.create_table(
        "master_data_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("import_type", sa.String(length=50), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=False),
        sa.Column("source_file_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="UPLOADED"),
        sa.Column("records_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_valid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_master_data_import_jobs_created_at", "master_data_import_jobs", ["created_at"])
    op.create_index("ix_master_data_import_jobs_status", "master_data_import_jobs", ["status"])

    op.create_table(
        "master_data_import_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("import_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("master_data_import_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("external_identifier", sa.String(length=150), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_data", postgresql.JSONB(), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_master_data_import_rows_import_job_id", "master_data_import_rows", ["import_job_id"])

    conn = op.get_bind()
    _seed_master_data(conn)


def downgrade() -> None:
    op.drop_table("master_data_import_rows")
    op.drop_table("master_data_import_jobs")
    op.drop_table("station_supplier_rules")
    op.drop_table("payment_terms")
    op.drop_table("distribution_bases")
    op.drop_table("erp_suppliers")
    op.drop_index("uq_distributors_org_cnpj", table_name="distributors")
    op.drop_table("distributors")
    op.drop_table("product_mapping_history")
    op.drop_table("erp_products")
    op.drop_table("products")
