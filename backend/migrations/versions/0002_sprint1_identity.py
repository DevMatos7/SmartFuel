"""Sprint 1 — organizações, postos, usuários, auth e auditoria."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_sprint1_identity"
down_revision: str | None = "0001_sprint0_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_SEEDS = [
    ("ADMIN", "Administrador", "Gestão total do sistema"),
    ("GESTOR", "Gestor", "Consulta gerencial autorizada"),
    ("COMPRADOR", "Comprador", "Acesso estrutural para compras futuras"),
    ("FINANCEIRO", "Financeiro", "Acesso estrutural para módulos financeiros"),
    ("CONSULTA", "Consulta", "Somente leitura"),
]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("corporate_name", sa.String(length=200), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("cnpj", name="uq_organizations_cnpj"),
    )

    op.create_table(
        "stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("station_type", sa.String(length=20), nullable=False),
        sa.Column("erp_branch_id", sa.String(length=50), nullable=True),
        sa.Column("corporate_name", sa.String(length=200), nullable=False),
        sa.Column("trade_name", sa.String(length=200), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("anp_code", sa.String(length=30), nullable=True),
        sa.Column("brand_type", sa.String(length=20), nullable=False),
        sa.Column("brand_name", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("cnpj", name="uq_stations_cnpj"),
        sa.UniqueConstraint("anp_code", name="uq_stations_anp_code"),
        sa.UniqueConstraint("organization_id", "erp_branch_id", name="uq_stations_org_erp_branch"),
    )
    op.create_index("ix_stations_organization_id", "stations", ["organization_id"])
    op.create_index("ix_stations_erp_branch_id", "stations", ["erp_branch_id"])
    op.execute(
        """
        CREATE UNIQUE INDEX ux_stations_one_headquarters_per_org
        ON stations (organization_id)
        WHERE station_type = 'HEADQUARTERS' AND active = true
        """
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("normalized_email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_all_stations_access", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    op.create_table(
        "user_stations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_user_stations_user_id", "user_stations", ["user_id"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("token_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_refresh_token_hash", "auth_sessions", ["refresh_token_hash"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    for code, name, description in ROLE_SEEDS:
        op.execute(
            sa.text(
                """
                INSERT INTO roles (id, code, name, description, active, created_at)
                SELECT gen_random_uuid(), :code, :name, :description, true, now()
                WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code = :code)
                """
            ).bindparams(code=code, name=name, description=description)
        )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("auth_sessions")
    op.drop_table("user_stations")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.execute("DROP INDEX IF EXISTS ux_stations_one_headquarters_per_org")
    op.drop_table("stations")
    op.drop_table("organizations")
