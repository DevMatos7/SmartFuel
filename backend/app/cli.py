"""CLI administrativa — bootstrap do primeiro administrador."""

import argparse
import asyncio
import getpass
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.role import Role, UserRole
from app.models.user import User
from app.services.audit_service import AuditContext, AuditService
from app.utils.cnpj import normalize_cnpj, validate_cnpj
from app.utils.email import normalize_email
from app.utils.password import validate_password


async def create_admin(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        existing_users = await db.execute(select(User))
        if existing_users.scalars().first() and not args.force:
            print("Já existe usuário cadastrado. Use --force apenas se souber o que está fazendo.")
            return

        org_name = args.org_name or input("Nome da organização: ").strip()
        org_corporate = args.org_corporate_name or input("Razão social da organização: ").strip()
        org_cnpj = normalize_cnpj(args.org_cnpj or input("CNPJ da organização: ").strip())
        if not validate_cnpj(org_cnpj):
            raise SystemExit("CNPJ inválido.")

        name = args.name or input("Nome do administrador: ").strip()
        email = args.email or input("E-mail do administrador: ").strip()
        password = args.password or getpass.getpass("Senha do administrador: ")
        password_confirm = args.password or getpass.getpass("Confirme a senha: ")
        if password != password_confirm:
            raise SystemExit("As senhas não conferem.")
        validate_password(password, email)

        org_result = await db.execute(select(Organization))
        org = org_result.scalars().first()
        if org is None:
            org = Organization(
                name=org_name,
                corporate_name=org_corporate,
                cnpj=org_cnpj,
                timezone=args.timezone,
                active=True,
            )
            db.add(org)
            await db.flush()

        admin_role = await db.execute(select(Role).where(Role.code == "ADMIN"))
        role = admin_role.scalar_one()

        normalized = normalize_email(email)
        dup = await db.execute(select(User).where(User.normalized_email == normalized))
        if dup.scalar_one_or_none():
            raise SystemExit("E-mail já cadastrado.")

        user = User(
            organization_id=org.id,
            name=name,
            email=email,
            normalized_email=normalized,
            password_hash=hash_password(password),
            active=True,
            must_change_password=args.must_change_password,
            has_all_stations_access=True,
        )
        db.add(user)
        await db.flush()
        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                created_at=datetime.now(UTC),
            )
        )

        audit = AuditService(db)
        await audit.log(
            ctx=AuditContext(organization_id=org.id, user_id=user.id, ip_address=None, request_id=None),
            entity_type="user",
            entity_id=user.id,
            action="bootstrap_admin",
            after_data={"email": email, "organization_id": str(org.id)},
            metadata={"source": "cli"},
        )
        from app.seeds.master_data import seed_master_data_for_organization
        from app.services.master_data_bootstrap_service import MasterDataBootstrapService

        bootstrap = MasterDataBootstrapService(db)
        await bootstrap.bootstrap_organization(
            organization_id=org.id,
            user_id=user.id,
            audit_ctx=AuditContext(organization_id=org.id, user_id=user.id, ip_address=None, request_id=None),
        )
        await db.commit()
        print(f"Administrador criado com sucesso: {email}")


async def seed_master_data_cmd(args: argparse.Namespace) -> None:
    org_id = uuid.UUID(args.organization_id)
    async with AsyncSessionLocal() as db:
        org = await db.get(Organization, org_id)
        if org is None:
            raise SystemExit("Organização não encontrada.")
        from app.services.master_data_bootstrap_service import MasterDataBootstrapService

        bootstrap = MasterDataBootstrapService(db)
        result = await bootstrap.bootstrap_organization(organization_id=org_id)
        await db.commit()
        print(f"Seed concluído: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ferramentas administrativas")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-admin", help="Cria o primeiro administrador")
    create.add_argument("--org-name")
    create.add_argument("--org-corporate-name")
    create.add_argument("--org-cnpj")
    create.add_argument("--timezone", default="America/Cuiaba")
    create.add_argument("--name")
    create.add_argument("--email")
    create.add_argument("--password")
    create.add_argument("--must-change-password", action="store_true", default=True)
    create.add_argument("--force", action="store_true")
    create.set_defaults(func=lambda args: asyncio.run(create_admin(args)))

    seed = sub.add_parser("seed-master-data", help="Cria produtos e condições iniciais para uma organização")
    seed.add_argument("--organization-id", required=True)
    seed.set_defaults(func=lambda args: asyncio.run(seed_master_data_cmd(args)))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
